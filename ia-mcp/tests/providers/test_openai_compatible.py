"""Testes do provedor OpenAI-compatible usando MockTransport (sem rede)."""

from __future__ import annotations

import json
from typing import Callable

import httpx
import pytest

from ia_mcp.domain.models import DemandaInsight, GrupoInsight
from ia_mcp.errors import (
    InvalidProviderResponseError,
    ProviderUnavailableError,
)
from ia_mcp.providers.openai_compatible import (
    OpenAICompatibleProvider,
    extract_json_object,
)
from ia_mcp.vocabulary.loader import Vocabulary

Handler = Callable[[httpx.Request], httpx.Response]


def chat_body(content: str) -> dict:
    return {"choices": [{"message": {"role": "assistant", "content": content}}]}


def make_provider(handler: Handler) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        base_url="http://ai.local/v1/",
        model="modelo-teste",
        api_key="segredo",
        timeout=5,
        transport=httpx.MockTransport(handler),
    )


def test_extract_json_object_handles_fences() -> None:
    assert extract_json_object('```json\n{"a": 1}\n```') == {"a": 1}


def test_extract_json_object_rejects_plain_text() -> None:
    with pytest.raises(InvalidProviderResponseError):
        extract_json_object("sem json aqui")


async def test_classify_filters_unknown_tags_and_clamps_confidence(
    vocabulary: Vocabulary,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "http://ai.local/v1/chat/completions"
        payload = json.loads(request.content)
        assert payload["model"] == "modelo-teste"
        assert request.headers["authorization"] == "Bearer segredo"
        return httpx.Response(
            200,
            json=chat_body(
                json.dumps(
                    {
                        "tags": ["conversao_vendas", "inventada", "conversao_vendas"],
                        "confidence": 4.2,
                    }
                )
            ),
        )

    outcome = await make_provider(handler).classify("texto", vocabulary)

    assert outcome.tags == ["conversao_vendas"]
    assert outcome.confidence == 1.0
    assert outcome.provider == "configured_model"
    assert outcome.fallback_used is False


async def test_classify_rejects_missing_tags(vocabulary: Vocabulary) -> None:
    provider = make_provider(
        lambda request: httpx.Response(200, json=chat_body(json.dumps({"a": 1})))
    )

    with pytest.raises(InvalidProviderResponseError):
        await provider.classify("texto", vocabulary)


async def test_classify_rejects_only_unknown_tags(vocabulary: Vocabulary) -> None:
    provider = make_provider(
        lambda request: httpx.Response(
            200, json=chat_body(json.dumps({"tags": ["inventada"]}))
        )
    )

    with pytest.raises(InvalidProviderResponseError):
        await provider.classify("texto", vocabulary)


async def test_http_error_becomes_unavailable(vocabulary: Vocabulary) -> None:
    provider = make_provider(lambda request: httpx.Response(503, text="fora do ar"))

    with pytest.raises(ProviderUnavailableError):
        await provider.classify("texto", vocabulary)


async def test_timeout_becomes_unavailable(vocabulary: Vocabulary) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("estourou", request=request)

    provider = make_provider(handler)

    with pytest.raises(ProviderUnavailableError):
        await provider.classify("texto", vocabulary)


async def test_invalid_provider_json_becomes_invalid_response(
    vocabulary: Vocabulary,
) -> None:
    provider = make_provider(
        lambda request: httpx.Response(200, json=chat_body("não é json"))
    )

    with pytest.raises(InvalidProviderResponseError):
        await provider.classify("texto", vocabulary)


async def test_invalid_envelope_becomes_invalid_response(
    vocabulary: Vocabulary,
) -> None:
    provider = make_provider(
        lambda request: httpx.Response(200, json={"choices": []})
    )

    with pytest.raises(InvalidProviderResponseError):
        await provider.classify("texto", vocabulary)


async def test_fenced_json_is_accepted(vocabulary: Vocabulary) -> None:
    content = '```json\n{"tags": ["pagamentos"], "confidence": 0.8}\n```'
    provider = make_provider(lambda request: httpx.Response(200, json=chat_body(content)))

    outcome = await provider.classify("texto", vocabulary)

    assert outcome.tags == ["pagamentos"]


async def test_summarize_returns_collapsed_text() -> None:
    provider = make_provider(
        lambda request: httpx.Response(200, json=chat_body("  Resumo   objetivo. "))
    )

    outcome = await provider.summarize("texto")

    assert outcome.resumo == "Resumo objetivo."
    assert outcome.provider == "configured_model"


async def test_summarize_rejects_empty_content() -> None:
    provider = make_provider(lambda request: httpx.Response(200, json=chat_body("  ")))

    with pytest.raises(InvalidProviderResponseError):
        await provider.summarize("texto")


async def test_interpret_maps_group_ids() -> None:
    groups = [
        GrupoInsight(
            id="g1",
            titulo="WhatsApp",
            demandas=[DemandaInsight(id="d1", texto="Não respondo à noite.")],
        ),
        GrupoInsight(id="g2", tags=["pagamentos"]),
    ]
    content = json.dumps({"g1": "Dificuldade de atendimento.", "g2": "Tema de pagamentos."})
    provider = make_provider(lambda request: httpx.Response(200, json=chat_body(content)))

    outcome = await provider.interpret(groups)

    assert outcome.interpretacoes == {
        "g1": "Dificuldade de atendimento.",
        "g2": "Tema de pagamentos.",
    }


async def test_interpret_accepts_wrapped_mapping() -> None:
    groups = [GrupoInsight(id="g1")]
    content = json.dumps({"interpretacoes": {"g1": "Interpretação."}})
    provider = make_provider(lambda request: httpx.Response(200, json=chat_body(content)))

    outcome = await provider.interpret(groups)

    assert outcome.interpretacoes == {"g1": "Interpretação."}


async def test_interpret_rejects_missing_group_key() -> None:
    groups = [GrupoInsight(id="g1"), GrupoInsight(id="g2")]
    content = json.dumps({"g1": "Somente um."})
    provider = make_provider(lambda request: httpx.Response(200, json=chat_body(content)))

    with pytest.raises(InvalidProviderResponseError):
        await provider.interpret(groups)


async def test_interpret_empty_groups_does_not_call_provider() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=chat_body("{}"))

    outcome = await make_provider(handler).interpret([])

    assert outcome.interpretacoes == {}
    assert calls == 0
