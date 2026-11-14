"""Testes dos contratos HTTP exatos exigidos pelo IAGateway."""

from __future__ import annotations

import logging
from typing import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI

from ia_mcp.config import Settings
from ia_mcp.domain.models import (
    ClassificationOutcome,
    GrupoInsight,
    InsightsOutcome,
    SummaryOutcome,
)
from ia_mcp.errors import ProviderUnavailableError
from ia_mcp.main import create_app
from ia_mcp.providers.chain import ProviderChain
from ia_mcp.vocabulary.loader import Vocabulary


class StubProvider:
    name = "stub"

    def __init__(self, *, mapping: dict[str, str] | None = None) -> None:
        self.mapping = mapping or {}

    async def classify(self, text: str, vocabulary: Vocabulary) -> ClassificationOutcome:
        return ClassificationOutcome(
            tags=["conversao_vendas", "inventada"],
            confidence=0.9,
            provider=self.name,
        )

    async def summarize(self, text: str) -> SummaryOutcome:
        return SummaryOutcome(resumo="Resumo objetivo.", provider=self.name)

    async def interpret(self, groups: list[GrupoInsight]) -> InsightsOutcome:
        return InsightsOutcome(
            interpretacoes={group.chave: f"Interpretação de {group.chave}." for group in groups},
            provider=self.name,
        )


class FailingProvider:
    name = "falha"

    async def classify(self, text: str, vocabulary: Vocabulary) -> ClassificationOutcome:
        raise ProviderUnavailableError("indisponível")

    async def summarize(self, text: str) -> SummaryOutcome:
        raise ProviderUnavailableError("indisponível")

    async def interpret(self, groups: list[GrupoInsight]) -> InsightsOutcome:
        raise ProviderUnavailableError("indisponível")


@pytest.fixture
def settings() -> Settings:
    return Settings(ai_provider="heuristic", _env_file=None)


@pytest.fixture
async def client(
    settings: Settings, vocabulary: Vocabulary
) -> AsyncIterator[httpx.AsyncClient]:
    app: FastAPI = create_app(
        settings,
        provider_chain=ProviderChain([StubProvider()]),
        vocabulary=vocabulary,
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://teste") as http:
        yield http


async def test_classificar_contract(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/ia/classificar", json={"texto": "Quero converter mais vendas"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body == {"tags": ["conversao_vendas"]}


async def test_resumir_contract(client: httpx.AsyncClient) -> None:
    response = await client.post("/ia/resumir", json={"texto": "Texto da demanda"})

    assert response.status_code == 200
    assert response.json() == {"resumo": "Resumo objetivo."}


async def test_insights_contract(client: httpx.AsyncClient) -> None:
    payload = {
        "grupos": [
            {
                "chave": "grupo-1",
                "titulo": "Atendimento",
                "quantidade": 3,
                "exemplos": ["Não respondo à noite."],
            },
            {"chave": "grupo-2"},
        ]
    }

    response = await client.post("/ia/insights", json=payload)

    assert response.status_code == 200
    assert response.json() == {
        "interpretacoes": {
            "grupo-1": "Interpretação de grupo-1.",
            "grupo-2": "Interpretação de grupo-2.",
        }
    }


async def test_insights_empty_groups_returns_empty_mapping(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post("/ia/insights", json={"grupos": []})

    assert response.status_code == 200
    assert response.json() == {"interpretacoes": {}}


async def test_text_is_not_logged_by_default(
    client: httpx.AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG, logger="ia_mcp.api.routes"):
        await client.post("/ia/resumir", json={"texto": "SEGREDO-NAO-LOGAR"})

    assert "SEGREDO-NAO-LOGAR" not in caplog.text


async def test_log_text_is_opt_in(
    vocabulary: Vocabulary, caplog: pytest.LogCaptureFixture
) -> None:
    settings = Settings(ai_provider="heuristic", log_text=True, _env_file=None)
    app = create_app(
        settings,
        provider_chain=ProviderChain([StubProvider()]),
        vocabulary=vocabulary,
    )
    transport = httpx.ASGITransport(app=app)

    with caplog.at_level(logging.DEBUG, logger="ia_mcp.api.routes"):
        async with httpx.AsyncClient(
            transport=transport, base_url="http://teste"
        ) as http:
            await http.post("/ia/resumir", json={"texto": "TEXTO-CAPTURADO"})

    assert "TEXTO-CAPTURADO" in caplog.text


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/ia/classificar", {"texto": "   "}),
        ("/ia/classificar", {}),
        ("/ia/resumir", {"texto": ""}),
        ("/ia/resumir", {}),
        ("/ia/insights", {}),
        ("/ia/insights", {"grupos": [{"chave": ""}]}),
    ],
)
async def test_invalid_payloads_return_422(
    client: httpx.AsyncClient, path: str, payload: dict
) -> None:
    response = await client.post(path, json=payload)

    assert response.status_code == 422


async def test_total_provider_failure_returns_503(
    settings: Settings, vocabulary: Vocabulary
) -> None:
    app = create_app(
        settings,
        provider_chain=ProviderChain([FailingProvider()]),
        vocabulary=vocabulary,
    )
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://teste") as http:
        for path, payload in [
            ("/ia/classificar", {"texto": "texto"}),
            ("/ia/resumir", {"texto": "texto"}),
            ("/ia/insights", {"grupos": [{"chave": "g1"}]}),
        ]:
            response = await http.post(path, json=payload)
            assert response.status_code == 503
            assert response.json() == {"detail": "Serviço de IA indisponível"}


async def test_openapi_exposes_only_expected_ia_routes(
    settings: Settings, vocabulary: Vocabulary
) -> None:
    app = create_app(
        settings,
        provider_chain=ProviderChain([StubProvider()]),
        vocabulary=vocabulary,
    )
    schema = app.openapi()

    assert set(schema["paths"]) == {
        "/ia/classificar",
        "/ia/resumir",
        "/ia/insights",
    }
