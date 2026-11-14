"""Serviço de classificação textual."""

from __future__ import annotations

from ia_mcp.domain.models import ClassificationOutcome
from ia_mcp.errors import ServiceUnavailableError
from ia_mcp.providers.chain import ProviderChain
from ia_mcp.text import truncate_words
from ia_mcp.vocabulary.loader import Vocabulary


class ClassificationService:
    """Classifica texto livre e garante que só retornem tags do vocabulário."""

    def __init__(
        self,
        chain: ProviderChain,
        vocabulary: Vocabulary,
        *,
        max_tags: int = 8,
        max_text_chars: int = 4000,
    ) -> None:
        self._chain = chain
        self._vocabulary = vocabulary
        self._max_tags = max_tags
        self._max_text_chars = max_text_chars

    async def classify(self, texto: str) -> ClassificationOutcome:
        text = texto.strip()
        if not text:
            raise ValueError("O texto não pode ser vazio")
        text = truncate_words(text, self._max_text_chars, suffix="")

        outcome = await self._chain.classify(text, self._vocabulary)

        tags: list[str] = []
        for tag in outcome.tags:
            if tag not in self._vocabulary or tag in tags:
                continue
            tags.append(tag)
            if len(tags) >= self._max_tags:
                break

        confidence = min(1.0, max(0.0, outcome.confidence))
        if not tags:
            confidence = 0.0

        result = outcome.model_copy(update={"tags": tags, "confidence": confidence})
        if result.provider == "unavailable":
            raise ServiceUnavailableError("Nenhum provedor de classificação disponível")
        return result


__all__ = ["ClassificationService"]
