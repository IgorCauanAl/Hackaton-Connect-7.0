"""Fachada interna do módulo.

A fachada organiza as chamadas dos serviços para uso interno e para testes. O
contrato externo com o backend é sempre HTTP (``/ia/*``); a fachada não o
substitui.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from ia_mcp.domain.models import GrupoInsight
from ia_mcp.services.classification import ClassificationService
from ia_mcp.services.insights import InsightsService
from ia_mcp.services.summarization import SummarizationService


@dataclass(frozen=True, slots=True)
class IAMCPService:
    """Agrupa os serviços de IA em uma única interface de chamada."""

    classification: ClassificationService
    summarization: SummarizationService
    insights: InsightsService

    async def classificar(self, texto: str) -> list[str]:
        outcome = await self.classification.classify(texto)
        return outcome.tags

    async def resumir(self, texto: str) -> str:
        outcome = await self.summarization.summarize(texto)
        return outcome.resumo

    async def interpretar(self, grupos: Sequence[GrupoInsight]) -> dict[str, str]:
        outcome = await self.insights.interpret(grupos)
        return outcome.interpretacoes


__all__ = ["IAMCPService"]
