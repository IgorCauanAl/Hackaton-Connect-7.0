"""Etapa 3 — classificação textual de ponta a ponta.

Exercita o fluxo real ``OpenAI-compatible → heurístico`` através do endpoint
``POST /ia/classificar``, usando ``httpx.MockTransport`` (sem rede).
"""

from __future__ import annotations

import json

import httpx
import pytest

from ia_mcp.config import Settings
from ia_mcp.domain.models import ClassificationOutcome
from ia_mcp.errors import ProviderUnavailableError
from ia_mcp.main import create_app
from ia_mcp.providers.chain import ProviderChain
from ia_mcp.providers.heuristic import HeuristicProvider
from ia_mcp.providers.openai_compatible import OpenAICompatibleProvider
from ia_mcp.vocabulary.loader import Vocabulary


def chat_body(content: str) -> dict:
    return {"choices": [{"message": {"role": "assistant", "content": content}}]}


def llm_provider(handler) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        base_url="http://ai.local/v1",
        model="modelo-teste",
        timeout=1,
        transport=httpx.MockTransport(handler),
    )


def make_app(chain: ProviderChain, vocabulary: Vocabulary):
    settings = Settings(ai_provider="heuristic", _env_file=None)
    return create_app(settings, provider_chain=chain, vocabulary=vocabulary)


async def classify(app, texto: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://teste") as client:
        return await client.post("/ia/classificar", json={"texto": texto})


class CountingHeuristic(HeuristicProvider):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.classify_calls = 0

    async def classify(
        self, text: str, vocabulary: Vocabulary
    ) -> ClassificationOutcome:
        self.classify_calls += 1
        return await super().classify(text, vocabulary)


class UnavailableHeuristic(HeuristicProvider):
    async def classify(
        self, text: str, vocabulary: Vocabulary
    ) -> ClassificationOutcome:
        raise ProviderUnavailableError("heurístico indisponível")


def successful_llm(tags: list[str], confidence: float = 0.9) -> OpenAICompatibleProvider:
    content = json.dumps({"tags": tags, "confidence": confidence})
    return llm_provider(lambda request: httpx.Response(200, json=chat_body(content)))


async def test_llm_result_is_filtered_by_vocabulary(vocabulary: Vocabulary) -> None:
    app = make_app(
        ProviderChain(
            [
                successful_llm(["atendimento_whatsapp", "tag_inventada"]),
                HeuristicProvider(),
            ]
        ),
        vocabulary,
    )

    response = await classify(app, "Preciso responder no WhatsApp")

    assert response.status_code == 200
    assert response.json() == {"tags": ["atendimento_whatsapp"]}


async def test_llm_success_does_not_call_heuristic(vocabulary: Vocabulary) -> None:
    heuristic = CountingHeuristic()
    app = make_app(
        ProviderChain([successful_llm(["pagamentos"]), heuristic]),
        vocabulary,
    )

    response = await classify(app, "Quero receber por Pix")

    assert response.status_code == 200
    assert response.json() == {"tags": ["pagamentos"]}
    assert heuristic.classify_calls == 0


async def test_http_error_falls_back_to_heuristic(
    vocabulary: Vocabulary, sample_text: str, expected_tags: set[str]
) -> None:
    app = make_app(
        ProviderChain(
            [
                llm_provider(lambda request: httpx.Response(500, text="erro")),
                HeuristicProvider(),
            ]
        ),
        vocabulary,
    )

    response = await classify(app, sample_text)

    assert response.status_code == 200
    assert set(response.json()["tags"]) == expected_tags


async def test_timeout_falls_back_to_heuristic(
    vocabulary: Vocabulary, sample_text: str, expected_tags: set[str]
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    app = make_app(
        ProviderChain([llm_provider(handler), HeuristicProvider()]),
        vocabulary,
    )

    response = await classify(app, sample_text)

    assert response.status_code == 200
    assert set(response.json()["tags"]) == expected_tags


async def test_invalid_provider_json_falls_back_to_heuristic(
    vocabulary: Vocabulary, sample_text: str
) -> None:
    app = make_app(
        ProviderChain(
            [
                llm_provider(
                    lambda request: httpx.Response(200, json=chat_body("não é json"))
                ),
                HeuristicProvider(),
            ]
        ),
        vocabulary,
    )

    response = await classify(app, sample_text)

    assert response.status_code == 200
    assert response.json()["tags"]


async def test_only_invalid_llm_tags_falls_back_to_heuristic(
    vocabulary: Vocabulary, sample_text: str, expected_tags: set[str]
) -> None:
    app = make_app(
        ProviderChain(
            [
                successful_llm(["inventada_1", "inventada_2"]),
                HeuristicProvider(),
            ]
        ),
        vocabulary,
    )

    response = await classify(app, sample_text)

    assert response.status_code == 200
    assert set(response.json()["tags"]) == expected_tags


async def test_no_match_returns_200_with_empty_tags(vocabulary: Vocabulary) -> None:
    app = make_app(ProviderChain([HeuristicProvider()]), vocabulary)

    response = await classify(app, "O tempo está nublado hoje.")

    assert response.status_code == 200
    assert response.json() == {"tags": []}


async def test_real_providers_total_failure_returns_503(
    vocabulary: Vocabulary,
) -> None:
    app = make_app(
        ProviderChain(
            [
                llm_provider(lambda request: httpx.Response(503, text="fora do ar")),
                UnavailableHeuristic(),
            ]
        ),
        vocabulary,
    )

    response = await classify(app, "Qualquer texto")

    assert response.status_code == 503
    assert response.json() == {"detail": "Serviço de IA indisponível"}


async def test_response_exposes_only_tags(vocabulary: Vocabulary) -> None:
    app = make_app(ProviderChain([successful_llm(["pagamentos"])]), vocabulary)

    response = await classify(app, "Quero receber por Pix")

    assert set(response.json()) == {"tags"}


@pytest.mark.parametrize("texto", ["", "   "])
async def test_empty_text_is_rejected(vocabulary: Vocabulary, texto: str) -> None:
    app = make_app(ProviderChain([HeuristicProvider()]), vocabulary)

    response = await classify(app, texto)

    assert response.status_code == 422
