"""Provedor local determinístico, usado como fallback quando não há LLM.

O heurístico nunca faz rede. Ele é intencionalmente simples: correspondência
lexical para classificação, resumo extrativo e interpretação por template.
"""

from __future__ import annotations

import re
from typing import Sequence

from ia_mcp.domain.models import (
    ClassificationOutcome,
    GrupoInsight,
    InsightsOutcome,
    SummaryOutcome,
)
from ia_mcp.errors import ProviderUnavailableError
from ia_mcp.text import collapse_whitespace, truncate_words
from ia_mcp.vocabulary.loader import TagDefinition, Vocabulary, normalize_text

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _keywords_for(definition: TagDefinition) -> tuple[str, ...]:
    if definition.keywords:
        return definition.keywords
    derived = [definition.tag.replace("_", " ")]
    if definition.label:
        derived.append(definition.label)
    return tuple(derived)


def _keyword_hits(normalized_text: str, keyword: str) -> bool:
    normalized_keyword = normalize_text(keyword)
    if not normalized_keyword:
        return False
    pattern = re.compile(rf"(?<!\w){re.escape(normalized_keyword)}(?!\w)")
    return pattern.search(normalized_text) is not None


def _extractive_summary(text: str, limit: int) -> str:
    collapsed = collapse_whitespace(text)
    if not collapsed:
        raise ProviderUnavailableError("Texto vazio não pode ser resumido")
    if len(collapsed) <= limit:
        return collapsed

    selected: list[str] = []
    for sentence in _SENTENCE_SPLIT.split(collapsed):
        sentence = sentence.strip()
        if not sentence:
            continue
        candidate = " ".join([*selected, sentence])
        if len(candidate) > limit:
            break
        selected.append(sentence)

    if selected:
        return " ".join(selected)
    return truncate_words(collapsed, limit)


class HeuristicProvider:
    """Fallback offline baseado em regras determinísticas."""

    name = "heuristic_fallback"

    def __init__(
        self,
        *,
        max_summary_chars: int = 600,
        max_insight_chars: int = 400,
        min_tag_confidence: float = 0.35,
    ) -> None:
        self._max_summary_chars = max_summary_chars
        self._max_insight_chars = max_insight_chars
        self._min_tag_confidence = min_tag_confidence

    async def classify(
        self, text: str, vocabulary: Vocabulary
    ) -> ClassificationOutcome:
        normalized = normalize_text(text)
        scored: list[tuple[int, str, float]] = []

        for definition in vocabulary.definitions:
            score = sum(
                1
                for keyword in _keywords_for(definition)
                if _keyword_hits(normalized, keyword)
            )
            if not score:
                continue
            confidence = min(0.95, 0.55 + 0.1 * (score - 1))
            if confidence >= self._min_tag_confidence:
                scored.append((score, definition.tag, confidence))

        scored.sort(key=lambda item: (-item[0], item[1]))
        tags = [tag for _, tag, _ in scored]
        confidence = max((value for _, _, value in scored), default=0.0)

        return ClassificationOutcome(
            tags=tags,
            confidence=confidence,
            provider=self.name,
        )

    async def summarize(self, text: str) -> SummaryOutcome:
        return SummaryOutcome(
            resumo=_extractive_summary(text, self._max_summary_chars),
            provider=self.name,
        )

    async def interpret(
        self, groups: Sequence[GrupoInsight]
    ) -> InsightsOutcome:
        interpretacoes = {group.id: self._interpret_group(group) for group in groups}
        return InsightsOutcome(
            interpretacoes=interpretacoes,
            provider=self.name,
        )

    def _interpret_group(self, group: GrupoInsight) -> str:
        subject = (
            f'O grupo "{group.titulo}"'
            if group.titulo
            else f"O grupo {group.id}"
        )
        parts = [subject]

        if group.tags:
            readable = ", ".join(tag.replace("_", " ") for tag in group.tags)
            parts.append(f"abrange os temas {readable}")
        else:
            parts.append("não possui tags informadas")

        excerpts: list[str] = []
        for demanda in group.demandas[:2]:
            excerpt = truncate_words(collapse_whitespace(demanda.texto), 160)
            if excerpt:
                excerpts.append(excerpt)

        if excerpts:
            quoted = "; ".join(f'"{excerpt}"' for excerpt in excerpts)
            parts.append(f"e reúne relatos como {quoted}")

        interpretation = collapse_whitespace(" ".join(parts)) + "."
        return truncate_words(interpretation, self._max_insight_chars)


__all__ = ["HeuristicProvider"]
