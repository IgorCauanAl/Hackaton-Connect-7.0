"""Testes do provedor heurístico local."""

from __future__ import annotations

import pytest

from ia_mcp.domain.models import DemandaInsight, GrupoInsight
from ia_mcp.errors import ProviderUnavailableError
from ia_mcp.providers.heuristic import HeuristicProvider
from ia_mcp.vocabulary.loader import Vocabulary


async def test_classifies_sample_text_with_expected_tags(
    vocabulary: Vocabulary, sample_text: str, expected_tags: set[str]
) -> None:
    outcome = await HeuristicProvider().classify(sample_text, vocabulary)

    assert set(outcome.tags) == expected_tags
    assert outcome.provider == "heuristic_fallback"
    assert outcome.fallback_used is False
    assert 0.0 <= outcome.confidence <= 1.0


async def test_returns_no_tags_for_unrelated_text(vocabulary: Vocabulary) -> None:
    outcome = await HeuristicProvider().classify("O tempo está nublado hoje.", vocabulary)

    assert outcome.tags == []
    assert outcome.confidence == 0.0


async def test_is_deterministic(vocabulary: Vocabulary, sample_text: str) -> None:
    provider = HeuristicProvider()
    first = await provider.classify(sample_text, vocabulary)
    second = await provider.classify(sample_text, vocabulary)

    assert first == second


async def test_respects_min_tag_confidence(vocabulary: Vocabulary, sample_text: str) -> None:
    outcome = await HeuristicProvider(min_tag_confidence=0.99).classify(
        sample_text, vocabulary
    )

    assert outcome.tags == []
    assert outcome.confidence == 0.0


async def test_summarize_short_text_is_unchanged() -> None:
    outcome = await HeuristicProvider().summarize("  Preciso   de um site. ")

    assert outcome.resumo == "Preciso de um site."


async def test_summarize_truncates_long_text() -> None:
    provider = HeuristicProvider(max_summary_chars=60)
    text = "palavra " * 50

    outcome = await provider.summarize(text)

    assert len(outcome.resumo) <= 60
    assert outcome.resumo.endswith("…")


async def test_summarize_empty_text_raises() -> None:
    with pytest.raises(ProviderUnavailableError):
        await HeuristicProvider().summarize("   ")


async def test_interpret_returns_one_entry_per_group_without_counts() -> None:
    groups = [
        GrupoInsight(
            id="g1",
            titulo="WhatsApp",
            tags=["atendimento_whatsapp"],
            demandas=[
                DemandaInsight(id="d1", texto="Não consigo responder no WhatsApp."),
                DemandaInsight(id="d2", texto="Perco vendas à noite."),
                DemandaInsight(id="d3", texto="Cliente espera muito."),
            ],
        ),
        GrupoInsight(id="g2"),
    ]

    outcome = await HeuristicProvider().interpret(groups)

    assert set(outcome.interpretacoes) == {"g1", "g2"}
    assert all(value for value in outcome.interpretacoes.values())
    assert "3 demandas" not in outcome.interpretacoes["g1"]
    assert "whatsapp" in outcome.interpretacoes["g1"].lower()
    assert outcome.provider == "heuristic_fallback"


async def test_interpret_empty_groups() -> None:
    outcome = await HeuristicProvider().interpret([])

    assert outcome.interpretacoes == {}
