"""Aplicação FastAPI que expõe os contratos de IA e monta o servidor FastMCP.

Um único processo atende:

- ``POST /ia/classificar``
- ``POST /ia/resumir``
- ``POST /ia/insights``
- ``/mcp`` — protocolo MCP (Streamable HTTP)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ia_mcp.api.routes import router
from ia_mcp.backend.client import BackendClient
from ia_mcp.config import Settings
from ia_mcp.errors import ConfigurationError, ServiceUnavailableError
from ia_mcp.mcp.server import create_mcp_server
from ia_mcp.providers.base import AIProvider
from ia_mcp.providers.chain import ProviderChain
from ia_mcp.providers.heuristic import HeuristicProvider
from ia_mcp.providers.openai_compatible import OpenAICompatibleProvider
from ia_mcp.services.classification import ClassificationService
from ia_mcp.services.facade import IAMCPService
from ia_mcp.services.insights import InsightsService
from ia_mcp.services.summarization import SummarizationService
from ia_mcp.vocabulary.loader import Vocabulary

logger = logging.getLogger(__name__)


def build_provider_chain(
    settings: Settings,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
) -> ProviderChain:
    """Monta a cadeia LLM → heurístico conforme a configuração."""

    heuristic = HeuristicProvider(
        max_summary_chars=settings.max_summary_chars,
        min_tag_confidence=settings.min_tag_confidence,
    )

    if settings.ai_provider == "heuristic":
        return ProviderChain([heuristic])

    providers: list[AIProvider] = []
    if settings.ai_base_url and settings.ai_model:
        providers.append(
            OpenAICompatibleProvider(
                base_url=settings.ai_base_url,
                model=settings.ai_model,
                api_key=settings.ai_api_key,
                timeout=settings.ai_timeout_seconds,
                transport=transport,
            )
        )
    elif settings.ai_provider == "openai_compatible":
        raise ConfigurationError(
            "IA_MCP_AI_PROVIDER=openai_compatible exige IA_MCP_AI_BASE_URL e "
            "IA_MCP_AI_MODEL"
        )

    providers.append(heuristic)
    return ProviderChain(providers)


def load_vocabulary(settings: Settings) -> Vocabulary:
    """Carrega o vocabulário oficial/fornecido e os sinônimos locais."""

    keywords_path = settings.keywords_path
    return Vocabulary.from_file(
        settings.vocabulary_path,
        keywords_path if keywords_path.exists() else None,
    )


def build_service(
    settings: Settings, chain: ProviderChain, vocabulary: Vocabulary
) -> IAMCPService:
    return IAMCPService(
        classification=ClassificationService(
            chain,
            vocabulary,
            max_tags=settings.max_tags,
            max_text_chars=settings.max_text_chars,
        ),
        summarization=SummarizationService(
            chain,
            max_summary_chars=settings.max_summary_chars,
            max_text_chars=settings.max_text_chars,
        ),
        insights=InsightsService(chain),
    )


def configure_logging(settings: Settings) -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def create_app(
    settings: Settings | None = None,
    *,
    provider_chain: ProviderChain | None = None,
    backend_client: BackendClient | None = None,
    vocabulary: Vocabulary | None = None,
) -> FastAPI:
    """Cria a aplicação. Dependências podem ser injetadas em testes."""

    settings = settings or Settings()
    configure_logging(settings)

    vocabulary = vocabulary or load_vocabulary(settings)
    chain = provider_chain or build_provider_chain(settings)
    backend_client = backend_client or BackendClient(
        base_url=settings.backend_base_url,
        timeout=settings.backend_timeout_seconds,
    )
    service = build_service(settings, chain, vocabulary)

    mcp = create_mcp_server(backend_client)
    mcp_app = mcp.http_app(path="/")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with mcp_app.lifespan(app):
            yield

    app = FastAPI(
        title="IA/MCP — FACESP Match",
        version="0.1.0",
        description=(
            "Serviço de classificação, resumo e insights do FACESP Match, com "
            "ferramentas MCP somente leitura."
        ),
        lifespan=lifespan,
    )

    app.state.settings = settings
    app.state.ia = service
    app.state.backend = backend_client
    app.state.mcp = mcp

    app.include_router(router)
    app.mount(settings.mcp_path, mcp_app)

    @app.exception_handler(ServiceUnavailableError)
    async def _service_unavailable(
        request: Request, exc: ServiceUnavailableError
    ) -> JSONResponse:
        logger.warning("Serviço de IA indisponível: %s", exc)
        return JSONResponse(
            status_code=503,
            content={"detail": "Serviço de IA indisponível"},
        )

    return app


app = create_app()


if __name__ == "__main__":  # pragma: no cover - entrypoint manual
    _settings = Settings()
    uvicorn.run(
        "ia_mcp.main:app",
        host=_settings.api_host,
        port=_settings.api_port,
        reload=False,
    )
