"""Cadeia de provedores com fallback técnico."""

from __future__ import annotations

import logging
from typing import Sequence

from ia_mcp.domain.models import (
    ClassificationOutcome,
    GrupoInsight,
    InsightsOutcome,
    SummaryOutcome,
)
from ia_mcp.errors import (
    InvalidProviderResponseError,
    ProviderUnavailableError,
    ServiceUnavailableError,
)
from ia_mcp.providers.base import AIProvider
from ia_mcp.vocabulary.loader import Vocabulary

logger = logging.getLogger(__name__)

_FALLBACK_ERRORS = (ProviderUnavailableError, InvalidProviderResponseError)


class ProviderChain:
    """Executa os provedores em ordem até um deles responder.

    Se todos falharem tecnicamente, levanta ``ServiceUnavailableError``, que a
    camada HTTP converte em ``503``.
    """

    def __init__(self, providers: Sequence[AIProvider]) -> None:
        self._providers = tuple(providers)
        if not self._providers:
            raise ValueError("A cadeia precisa de ao menos um provedor")

    @property
    def providers(self) -> tuple[AIProvider, ...]:
        return self._providers

    async def _first(self, method: str, *args: object) -> tuple[int, object]:
        failures: list[str] = []
        for index, provider in enumerate(self._providers):
            try:
                result = await getattr(provider, method)(*args)
                return index, result
            except _FALLBACK_ERRORS as exc:
                failures.append(f"{provider.name}: {exc}")
                logger.warning(
                    "Provedor '%s' falhou em '%s': %s", provider.name, method, exc
                )
        raise ServiceUnavailableError(
            "Todos os provedores de IA falharam: " + "; ".join(failures)
        )

    async def classify(
        self, text: str, vocabulary: Vocabulary
    ) -> ClassificationOutcome:
        index, result = await self._first("classify", text, vocabulary)
        assert isinstance(result, ClassificationOutcome)
        return result.model_copy(
            update={"fallback_used": result.fallback_used or index > 0}
        )

    async def summarize(self, text: str) -> SummaryOutcome:
        index, result = await self._first("summarize", text)
        assert isinstance(result, SummaryOutcome)
        return result.model_copy(
            update={"fallback_used": result.fallback_used or index > 0}
        )

    async def interpret(
        self, groups: Sequence[GrupoInsight]
    ) -> InsightsOutcome:
        index, result = await self._first("interpret", groups)
        assert isinstance(result, InsightsOutcome)
        return result.model_copy(
            update={"fallback_used": result.fallback_used or index > 0}
        )


__all__ = ["ProviderChain"]
