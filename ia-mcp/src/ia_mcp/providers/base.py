"""Contrato interno dos provedores de IA."""

from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable

from ia_mcp.domain.models import (
    ClassificationOutcome,
    GrupoInsight,
    InsightsOutcome,
    SummaryOutcome,
)
from ia_mcp.vocabulary.loader import Vocabulary


@runtime_checkable
class AIProvider(Protocol):
    """Interface desacoplada de um provedor de IA.

    Implementações devem levantar ``ProviderUnavailableError`` para falhas
    técnicas (rede, timeout, HTTP, configuração) e
    ``InvalidProviderResponseError`` para respostas não interpretáveis. Assim a
    cadeia de provedores consegue aplicar o fallback.
    """

    name: str

    async def classify(
        self, text: str, vocabulary: Vocabulary
    ) -> ClassificationOutcome: ...

    async def summarize(self, text: str) -> SummaryOutcome: ...

    async def interpret(
        self, groups: Sequence[GrupoInsight]
    ) -> InsightsOutcome: ...


__all__ = ["AIProvider"]
