"""Testes dos utilitários de texto."""

from __future__ import annotations

from ia_mcp.text import collapse_whitespace, truncate_words


def test_collapse_whitespace() -> None:
    assert collapse_whitespace("  muito   espaço\n\naqui ") == "muito espaço aqui"


def test_truncate_words_keeps_short_text() -> None:
    assert truncate_words("texto curto", 50) == "texto curto"


def test_truncate_words_respects_limit_and_word_boundary() -> None:
    result = truncate_words("uma frase com varias palavras", 15)

    assert len(result) <= 15
    assert result.endswith("…")


def test_truncate_words_without_suffix() -> None:
    result = truncate_words("uma frase com varias palavras", 15, suffix="")

    assert len(result) <= 15
    assert not result.endswith("…")


def test_truncate_words_zero_limit() -> None:
    assert truncate_words("qualquer", 0) == ""
