"""Testes da cadeia de fallback entre provedores."""

from __future__ import annotations

import pytest

from ia_mcp.domain.models import (
    ClassificationOutcome,
    GrupoInsight,
    InsightsOutcome,
    SummaryOutcome,
)
from ia_mcp.errors import (
    ProviderUnavailableError,
    ServiceUnavailableError,
)
from ia_mcp.providers.chain import ProviderChain
from ia_mcp.vocabulary.loader import Vocabulary


class FailingProvider:
    name = "falha"

    async def classify(self, text: str, vocabulary: Vocabulary) -> ClassificationOutcome:
        raise ProviderUnavailableError("indisponível")

    async def summarize(self, text: str) -> SummaryOutcome:
        raise ProviderUnavailableError("indisponível")

    async def interpret(self, groups: list[GrupoInsight]) -> InsightsOutcome:
        raise ProviderUnavailableError("indisponível")


class WorkingProvider:
    name = "ok"

    async def classify(self, text: str, vocabulary: Vocabulary) -> ClassificationOutcome:
        return ClassificationOutcome(tags=["pagamentos"], confidence=0.7, provider=self.name)

    async def summarize(self, text: str) -> SummaryOutcome:
        return SummaryOutcome(resumo="Resumo.", provider=self.name)

    async def interpret(self, groups: list[GrupoInsight]) -> InsightsOutcome:
        return InsightsOutcome(
            interpretacoes={group.chave: "Interpretação." for group in groups},
            provider=self.name,
        )


async def test_uses_fallback_when_first_provider_fails(vocabulary: Vocabulary) -> None:
    chain = ProviderChain([FailingProvider(), WorkingProvider()])

    outcome = await chain.classify("texto", vocabulary)

    assert outcome.tags == ["pagamentos"]
    assert outcome.provider == "ok"
    assert outcome.fallback_used is True


async def test_first_provider_success_does_not_set_fallback(vocabulary: Vocabulary) -> None:
    chain = ProviderChain([WorkingProvider(), FailingProvider()])

    outcome = await chain.classify("texto", vocabulary)

    assert outcome.fallback_used is False


async def test_raises_service_unavailable_when_all_fail(vocabulary: Vocabulary) -> None:
    chain = ProviderChain([FailingProvider(), FailingProvider()])

    with pytest.raises(ServiceUnavailableError):
        await chain.classify("texto", vocabulary)

    with pytest.raises(ServiceUnavailableError):
        await chain.summarize("texto")

    with pytest.raises(ServiceUnavailableError):
        await chain.interpret([GrupoInsight(chave="g1")])


async def test_summarize_and_interpret_fallbacks() -> None:
    chain = ProviderChain([FailingProvider(), WorkingProvider()])

    summary = await chain.summarize("texto")
    insights = await chain.interpret([GrupoInsight(chave="g1")])

    assert summary.resumo == "Resumo."
    assert summary.fallback_used is True
    assert insights.interpretacoes == {"g1": "Interpretação."}
    assert insights.fallback_used is True


def test_chain_requires_provider() -> None:
    with pytest.raises(ValueError):
        ProviderChain([])
