"""Serviço de interpretação de grupos de demandas."""

from __future__ import annotations

from typing import Sequence

from ia_mcp.domain.models import GrupoInsight, InsightsOutcome
from ia_mcp.errors import ServiceUnavailableError
from ia_mcp.providers.chain import ProviderChain


class InsightsService:
    """Produz uma interpretação textual por grupo, sem calcular métricas."""

    def __init__(self, chain: ProviderChain) -> None:
        self._chain = chain

    async def interpret(self, grupos: Sequence[GrupoInsight]) -> InsightsOutcome:
        if not grupos:
            return InsightsOutcome(interpretacoes={}, provider="none")

        outcome = await self._chain.interpret(grupos)

        ordered: dict[str, str] = {}
        for group in grupos:
            value = outcome.interpretacoes.get(group.chave)
            if not isinstance(value, str) or not value.strip():
                raise ServiceUnavailableError(
                    f"Não foi possível interpretar o grupo '{group.chave}'"
                )
            ordered[group.chave] = value.strip()

        return outcome.model_copy(update={"interpretacoes": ordered})


__all__ = ["InsightsService"]
