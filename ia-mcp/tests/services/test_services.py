"""Testes dos serviços internos e da fachada."""

from __future__ import annotations

import pytest

from ia_mcp.domain.models import (
    ClassificationOutcome,
    GrupoInsight,
    InsightsOutcome,
    SummaryOutcome,
)
from ia_mcp.errors import ServiceUnavailableError
from ia_mcp.providers.chain import ProviderChain
from ia_mcp.services.classification import ClassificationService
from ia_mcp.services.facade import IAMCPService
from ia_mcp.services.insights import InsightsService
from ia_mcp.services.summarization import SummarizationService
from ia_mcp.vocabulary.loader import Vocabulary


class FakeProvider:
    name = "fake"

    def __init__(
        self,
        *,
        tags: list[str] | None = None,
        confidence: float = 0.8,
        resumo: str = "Resumo.",
        mapping: dict[str, str] | None = None,
        provider_name: str = "fake",
    ) -> None:
        self.tags = tags or []
        self.confidence = confidence
        self.resumo = resumo
        self.mapping = mapping or {}
        self.name = provider_name
        self.calls = 0
        self.last_text: str | None = None

    async def classify(self, text: str, vocabulary: Vocabulary) -> ClassificationOutcome:
        self.calls += 1
        self.last_text = text
        return ClassificationOutcome(
            tags=self.tags,
            confidence=self.confidence,
            provider=self.name,
        )

    async def summarize(self, text: str) -> SummaryOutcome:
        self.calls += 1
        self.last_text = text
        return SummaryOutcome(resumo=self.resumo, provider=self.name)

    async def interpret(self, groups: list[GrupoInsight]) -> InsightsOutcome:
        self.calls += 1
        return InsightsOutcome(
            interpretacoes=dict(self.mapping),
            provider=self.name,
        )


async def test_classification_filters_vocabulary_dedupes_and_caps(
    vocabulary: Vocabulary,
) -> None:
    provider = FakeProvider(
        tags=[
            "pagamentos",
            "inventada",
            "pagamentos",
            "controle_estoque",
            "conversao_vendas",
        ]
    )
    service = ClassificationService(ProviderChain([provider]), vocabulary, max_tags=2)

    outcome = await service.classify("texto")

    assert outcome.tags == ["pagamentos", "controle_estoque"]


async def test_classification_clamps_confidence(vocabulary: Vocabulary) -> None:
    provider = FakeProvider(tags=["pagamentos"], confidence=9.0)
    service = ClassificationService(ProviderChain([provider]), vocabulary)

    outcome = await service.classify("texto")

    assert outcome.confidence == 1.0


async def test_classification_zero_confidence_when_no_tags(
    vocabulary: Vocabulary,
) -> None:
    provider = FakeProvider(tags=["inventada"], confidence=0.9)
    service = ClassificationService(ProviderChain([provider]), vocabulary)

    outcome = await service.classify("texto")

    assert outcome.tags == []
    assert outcome.confidence == 0.0


async def test_classification_rejects_empty_text(vocabulary: Vocabulary) -> None:
    service = ClassificationService(ProviderChain([FakeProvider()]), vocabulary)

    with pytest.raises(ValueError):
        await service.classify("   ")


async def test_classification_truncates_long_text(vocabulary: Vocabulary) -> None:
    provider = FakeProvider(tags=["pagamentos"])
    service = ClassificationService(
        ProviderChain([provider]), vocabulary, max_text_chars=20
    )

    await service.classify("palavra " * 20)

    assert provider.last_text is not None
    assert len(provider.last_text) <= 20


async def test_summarization_truncates_long_input() -> None:
    provider = FakeProvider(resumo="Resumo.")
    service = SummarizationService(ProviderChain([provider]), max_text_chars=15)

    await service.summarize("palavra " * 20)

    assert provider.last_text is not None
    assert len(provider.last_text) <= 15


async def test_classification_unavailable_provider_raises(
    vocabulary: Vocabulary,
) -> None:
    provider = FakeProvider(tags=[], provider_name="unavailable")
    service = ClassificationService(ProviderChain([provider]), vocabulary)

    with pytest.raises(ServiceUnavailableError):
        await service.classify("texto")


async def test_summarization_truncates_provider_output() -> None:
    provider = FakeProvider(resumo="palavra " * 50)
    service = SummarizationService(ProviderChain([provider]), max_summary_chars=40)

    outcome = await service.summarize("texto")

    assert len(outcome.resumo) <= 40
    assert outcome.resumo.endswith("…")


async def test_summarization_rejects_blank_provider_output() -> None:
    provider = FakeProvider(resumo="   ")
    service = SummarizationService(ProviderChain([provider]))

    with pytest.raises(ServiceUnavailableError):
        await service.summarize("texto")


async def test_insights_orders_keys_as_input() -> None:
    provider = FakeProvider(mapping={"g2": "B", "g1": "A"})
    service = InsightsService(ProviderChain([provider]))

    outcome = await service.interpret([GrupoInsight(chave="g1"), GrupoInsight(chave="g2")])

    assert list(outcome.interpretacoes) == ["g1", "g2"]
    assert outcome.interpretacoes == {"g1": "A", "g2": "B"}


async def test_insights_missing_group_raises() -> None:
    provider = FakeProvider(mapping={"g1": "A"})
    service = InsightsService(ProviderChain([provider]))

    with pytest.raises(ServiceUnavailableError):
        await service.interpret([GrupoInsight(chave="g1"), GrupoInsight(chave="g2")])


async def test_insights_empty_groups_does_not_call_provider() -> None:
    provider = FakeProvider()
    service = InsightsService(ProviderChain([provider]))

    outcome = await service.interpret([])

    assert outcome.interpretacoes == {}
    assert provider.calls == 0


async def test_facade_delegates(vocabulary: Vocabulary) -> None:
    provider = FakeProvider(
        tags=["pagamentos"],
        resumo="Resumo curto.",
        mapping={"g1": "Interpretação."},
    )
    chain = ProviderChain([provider])
    facade = IAMCPService(
        classification=ClassificationService(chain, vocabulary),
        summarization=SummarizationService(chain),
        insights=InsightsService(chain),
    )

    assert await facade.classificar("texto") == ["pagamentos"]
    assert await facade.resumir("texto") == "Resumo curto."
    assert await facade.interpretar(
        [GrupoInsight(chave="g1", exemplos=["x"])]
    ) == {"g1": "Interpretação."}
