"""Serviço de resumo de demandas."""

from __future__ import annotations

from ia_mcp.domain.models import SummaryOutcome
from ia_mcp.errors import ServiceUnavailableError
from ia_mcp.providers.chain import ProviderChain
from ia_mcp.text import collapse_whitespace, truncate_words


class SummarizationService:
    """Gera um resumo objetivo com fallback extrativo."""

    def __init__(
        self,
        chain: ProviderChain,
        *,
        max_summary_chars: int = 600,
        max_text_chars: int = 4000,
    ) -> None:
        self._chain = chain
        self._max_summary_chars = max_summary_chars
        self._max_text_chars = max_text_chars

    async def summarize(self, texto: str) -> SummaryOutcome:
        text = collapse_whitespace(texto)
        if not text:
            raise ValueError("O texto não pode ser vazio")
        text = truncate_words(text, self._max_text_chars, suffix="")

        outcome = await self._chain.summarize(text)
        resumo = truncate_words(collapse_whitespace(outcome.resumo), self._max_summary_chars)
        if not resumo:
            raise ServiceUnavailableError("Não foi possível gerar o resumo")

        return outcome.model_copy(update={"resumo": resumo})


__all__ = ["SummarizationService"]
