"""Utilitários de texto compartilhados por provedores e serviços."""

from __future__ import annotations

import re

_WHITESPACE = re.compile(r"\s+")


def collapse_whitespace(text: str) -> str:
    """Remove espaços repetidos e das extremidades."""

    return _WHITESPACE.sub(" ", text).strip()


def truncate_words(text: str, limit: int, suffix: str = "…") -> str:
    """Trunca texto respeitando limites de palavra e o tamanho final."""

    if limit <= 0:
        return ""
    if len(text) <= limit:
        return text
    if limit == 1:
        return suffix[:1]

    cut = text[: limit - len(suffix)]
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    cut = cut.rstrip(" ,;:-")
    if not cut:
        return text[:limit]
    return f"{cut}{suffix}"


__all__ = ["collapse_whitespace", "truncate_words"]
