"""Teste de integração do processo único: FastAPI + FastMCP."""

from __future__ import annotations

import httpx

from ia_mcp.config import Settings
from ia_mcp.domain.models import (
    ClassificationOutcome,
    GrupoInsight,
    InsightsOutcome,
    SummaryOutcome,
)
from ia_mcp.main import create_app
from ia_mcp.providers.chain import ProviderChain
from ia_mcp.vocabulary.loader import Vocabulary


class StubProvider:
    name = "stub"

    async def classify(self, text: str, vocabulary: Vocabulary) -> ClassificationOutcome:
        return ClassificationOutcome(tags=[], confidence=0.0, provider=self.name)

    async def summarize(self, text: str) -> SummaryOutcome:
        return SummaryOutcome(resumo="Resumo.", provider=self.name)

    async def interpret(self, groups: list[GrupoInsight]) -> InsightsOutcome:
        return InsightsOutcome(
            interpretacoes={group.chave: "Interpretação." for group in groups},
            provider=self.name,
        )


async def test_single_process_serves_ia_routes_and_mcp(
    vocabulary: Vocabulary,
) -> None:
    settings = Settings(ai_provider="heuristic", mcp_path="/mcp", _env_file=None)
    app = create_app(
        settings,
        provider_chain=ProviderChain([StubProvider()]),
        vocabulary=vocabulary,
    )

    mounts = {
        getattr(route, "path", None)
        for route in app.routes
        if route.__class__.__name__ == "Mount"
    }
    assert "/mcp" in mounts

    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport, base_url="http://teste"
        ) as client:
            response = await client.post(
                "/ia/resumir", json={"texto": "Uma demanda qualquer."}
            )
            assert response.status_code == 200
            assert response.json() == {"resumo": "Resumo."}

            initialize = await client.post(
                "/mcp/",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {},
                        "clientInfo": {"name": "teste", "version": "0.1"},
                    },
                },
                headers={
                    "Accept": "application/json, text/event-stream",
                    "Content-Type": "application/json",
                },
            )
            assert initialize.status_code == 200
            assert "ia-mcp-facesp" in initialize.text
