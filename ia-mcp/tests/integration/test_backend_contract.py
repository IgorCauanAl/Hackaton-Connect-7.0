"""Contrato real entre o backend operacional e o IA/MCP.

Diferente dos demais testes, este usa o **vocabulário oficial** embarcado no
pacote e um payload de insights no formato exato produzido por
``RadarService.gerar_insights``. Também garante que a cópia local do
vocabulário não diverge de ``back-end/config/vocabulario.json``.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from ia_mcp.config import DEFAULT_KEYWORDS_PATH, DEFAULT_VOCABULARY_PATH, Settings
from ia_mcp.main import create_app
from ia_mcp.providers.chain import ProviderChain
from ia_mcp.providers.heuristic import HeuristicProvider
from ia_mcp.vocabulary.loader import Vocabulary

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_VOCABULARY = REPO_ROOT / "back-end" / "config" / "vocabulario.json"


def official_vocabulary() -> Vocabulary:
    return Vocabulary.from_file(DEFAULT_VOCABULARY_PATH, DEFAULT_KEYWORDS_PATH)


@pytest.fixture
def app():
    settings = Settings(ai_provider="heuristic", _env_file=None)
    return create_app(
        settings,
        provider_chain=ProviderChain([HeuristicProvider()]),
        vocabulary=official_vocabulary(),
    )


def only_tags(path: Path) -> set[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data["tags"] if isinstance(data, dict) else data
    return {
        item["tag"] if isinstance(item, dict) else item
        for item in items
    }


def test_embedded_vocabulary_matches_backend() -> None:
    if not BACKEND_VOCABULARY.exists():  # pragma: no cover - repositório isolado
        pytest.skip("back-end/config/vocabulario.json não disponível")

    assert only_tags(DEFAULT_VOCABULARY_PATH) == only_tags(BACKEND_VOCABULARY)


async def test_classificar_returns_only_official_tags(app) -> None:
    texto = (
        "Não consigo responder no WhatsApp e vivo perdendo venda. "
        "Meu estoque também está desorganizado."
    )

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://teste") as client:
        response = await client.post("/ia/classificar", json={"texto": texto})

    assert response.status_code == 200
    tags = response.json()["tags"]
    assert tags
    assert set(tags) <= official_vocabulary().tags
    assert {"whatsapp", "estoque"} <= set(tags)


async def test_insights_accepts_real_backend_payload(app) -> None:
    payload = {
        "grupos": [
            {
                "chave": "atendimento",
                "titulo": "Atendimento",
                "quantidade": 7,
                "exemplos": [
                    "Não consigo responder no WhatsApp fora do horário.",
                    "Os clientes reclamam da demora.",
                ],
            },
            {
                "chave": "estoque",
                "titulo": "Estoque",
                "quantidade": 2,
                "exemplos": ["Não sei o que está em falta."],
            },
        ]
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://teste") as client:
        response = await client.post("/ia/insights", json=payload)

    assert response.status_code == 200
    interpretacoes = response.json()["interpretacoes"]
    assert set(interpretacoes) == {"atendimento", "estoque"}
    assert all(value.strip() for value in interpretacoes.values())
    assert "atendimento" in interpretacoes["atendimento"].lower()


async def test_insights_rejects_legacy_payload(app) -> None:
    legacy = {
        "grupos": [
            {
                "id": "grupo-1",
                "titulo": "Atendimento",
                "tags": ["whatsapp"],
                "demandas": [{"id": "d1", "texto": "x"}],
            }
        ]
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://teste") as client:
        response = await client.post("/ia/insights", json=legacy)

    assert response.status_code == 422
