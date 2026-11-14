"""Testes do carregamento e da normalização do vocabulário."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ia_mcp.errors import VocabularyError
from ia_mcp.vocabulary.loader import Vocabulary, normalize_text


def test_loads_simple_list(tmp_path: Path) -> None:
    path = tmp_path / "tags.json"
    path.write_text(json.dumps({"tags": ["alpha", "beta"]}), encoding="utf-8")

    vocabulary = Vocabulary.from_file(path)

    assert vocabulary.tags == {"alpha", "beta"}
    assert len(vocabulary) == 2
    assert "alpha" in vocabulary
    assert "gama" not in vocabulary


def test_loads_bare_list_format(tmp_path: Path) -> None:
    path = tmp_path / "tags.json"
    path.write_text(json.dumps(["alpha", "beta"]), encoding="utf-8")

    assert Vocabulary.from_file(path).tags == {"alpha", "beta"}


def test_loads_enriched_format(tmp_path: Path) -> None:
    path = tmp_path / "tags.json"
    path.write_text(
        json.dumps(
            {
                "tags": [
                    {
                        "tag": "whatsapp",
                        "label": "WhatsApp",
                        "keywords": ["zap", "mensagem"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    definition = Vocabulary.from_file(path).get("whatsapp")
    assert definition is not None
    assert definition.label == "WhatsApp"
    assert definition.keywords == ("zap", "mensagem")


def test_merges_keywords_only_for_known_tags(tmp_path: Path) -> None:
    tags = tmp_path / "tags.json"
    tags.write_text(json.dumps({"tags": [{"tag": "alpha", "keywords": ["a"]}]}))
    keywords = tmp_path / "keywords.json"
    keywords.write_text(json.dumps({"alpha": ["b"], "beta": ["c"], "_comment": "x"}))

    vocabulary = Vocabulary.from_file(tags, keywords)

    definition = vocabulary.get("alpha")
    assert definition is not None
    assert definition.keywords == ("a", "b")
    assert "beta" not in vocabulary


def test_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(VocabularyError):
        Vocabulary.from_file(tmp_path / "ausente.json")


def test_rejects_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "tags.json"
    path.write_text("{nao-e-json", encoding="utf-8")

    with pytest.raises(VocabularyError):
        Vocabulary.from_file(path)


def test_rejects_empty_vocabulary(tmp_path: Path) -> None:
    path = tmp_path / "tags.json"
    path.write_text(json.dumps({"tags": []}), encoding="utf-8")

    with pytest.raises(VocabularyError):
        Vocabulary.from_file(path)


def test_rejects_duplicate_tags(tmp_path: Path) -> None:
    path = tmp_path / "tags.json"
    path.write_text(json.dumps({"tags": ["alpha", "alpha"]}), encoding="utf-8")

    with pytest.raises(VocabularyError):
        Vocabulary.from_file(path)


def test_rejects_invalid_item(tmp_path: Path) -> None:
    path = tmp_path / "tags.json"
    path.write_text(json.dumps({"tags": [123]}), encoding="utf-8")

    with pytest.raises(VocabularyError):
        Vocabulary.from_file(path)


def test_normalize_text_removes_accents_case_and_punctuation() -> None:
    assert normalize_text("  Conversão de VENDAS! ") == "conversao de vendas"
    assert normalize_text("Fora-do-horário") == "fora do horario"
