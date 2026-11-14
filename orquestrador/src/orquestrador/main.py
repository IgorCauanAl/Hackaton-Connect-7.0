"""Aplicação FastAPI do Orquestrador (Módulo 03).

Atende React → Orquestrador → {Backend operacional, IA/MCP}.
"""

from __future__ import annotations

import logging
from time import perf_counter
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from orquestrador.api.routes import router
from orquestrador.clients.backend import BackendClient
from orquestrador.clients.ia import IAClient
from orquestrador.config import Settings
from orquestrador.container import Container
from orquestrador.errors import ErroDeOrquestracao
from orquestrador.idempotency import IdempotencyStore
from orquestrador.services.demandas import ServicoDemandas
from orquestrador.services.insights import ServicoInsights
from orquestrador.services.relatorios import ServicoRelatorios
from orquestrador.services.testes import ServicoTestes

logger = logging.getLogger(__name__)


def configure_logging(settings: Settings) -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _trace_id(request: Request) -> str:
    return getattr(request.state, "trace_id", "-")


def create_app(
    settings: Settings | None = None,
    *,
    backend_client: BackendClient | None = None,
    ia_client: IAClient | None = None,
) -> FastAPI:
    """Cria a aplicação. Clientes podem ser injetados nos testes."""

    settings = settings or Settings()
    configure_logging(settings)

    backend = backend_client or BackendClient(
        base_url=settings.backend_base_url,
        timeout=settings.backend_timeout_seconds,
    )
    ia = ia_client or IAClient(
        base_url=settings.ia_base_url,
        timeout=settings.ia_timeout_seconds,
    )

    container = Container(
        demandas=ServicoDemandas(backend, ia),
        insights=ServicoInsights(backend),
        testes=ServicoTestes(backend),
        relatorios=ServicoRelatorios(backend),
    )

    app = FastAPI(
        title="Orquestrador — FACESP Match",
        version="0.1.0",
        description=(
            "Coordena os fluxos entre o backend operacional e o serviço IA/MCP: "
            "demandas, matching, insights, testes e relatórios."
        ),
    )
    app.state.settings = settings
    app.state.container = container
    app.state.idempotencia = IdempotencyStore(settings.idempotency_ttl_seconds)

    @app.middleware("http")
    async def _trace_e_log(request: Request, call_next):
        request.state.trace_id = uuid4().hex[:12]
        inicio = perf_counter()
        response = await call_next(request)
        response.headers["X-Trace-Id"] = request.state.trace_id
        logger.info(
            "%s %s -> %s em %.0f ms trace_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            (perf_counter() - inicio) * 1000,
            request.state.trace_id,
        )
        return response

    @app.exception_handler(ErroDeOrquestracao)
    async def _erro_controlado(
        request: Request, exc: ErroDeOrquestracao
    ) -> JSONResponse:
        logger.warning(
            "Erro de orquestração trace_id=%s etapa=%s codigo=%s: %s",
            _trace_id(request),
            exc.etapa,
            exc.codigo,
            exc.detalhe,
        )
        return JSONResponse(
            status_code=exc.status,
            content={
                "detail": exc.detalhe,
                "codigo": exc.codigo,
                "etapa": exc.etapa,
                "trace_id": _trace_id(request),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def _erro_de_validacao(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "detail": jsonable_encoder(exc.errors()),
                "codigo": "requisicao_invalida",
                "etapa": "validacao",
                "trace_id": _trace_id(request),
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def _erro_http(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        codigos = {
            401: "ator_invalido",
            403: "acesso_negado",
            404: "nao_encontrado",
        }
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "codigo": codigos.get(exc.status_code, "requisicao_invalida"),
                "etapa": "validacao",
                "trace_id": _trace_id(request),
            },
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def _erro_inesperado(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception(
            "Erro inesperado trace_id=%s: %s", _trace_id(request), exc
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Erro interno do orquestrador.",
                "codigo": "erro_interno",
                "etapa": "orquestracao",
                "trace_id": _trace_id(request),
            },
        )

    app.include_router(router)

    @app.get("/health", tags=["infra"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "servico": "orquestrador"}

    return app


app = create_app()


if __name__ == "__main__":  # pragma: no cover - entrypoint manual
    _settings = Settings()
    uvicorn.run(
        "orquestrador.main:app",
        host=_settings.api_host,
        port=_settings.api_port,
        reload=False,
    )
