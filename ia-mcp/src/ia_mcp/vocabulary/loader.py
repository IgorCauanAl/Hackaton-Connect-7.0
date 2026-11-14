"""Carregamento e validação do vocabulário controlado de tags.

O vocabulário é um artefato **fornecido pelo backend operacional**. O arquivo
padrão incluído neste pacote é apenas um substituto de desenvolvimento e deve
ser trocado pelo JSON oficial antes da integração final.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ia_mcp.errors import VocabularyError

logger = logging.getLogger(__name__)

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize_text(text: str) -> str:
    """Normaliza texto para comparação lexical.

    Remove acentos, ignora caixa e troca qualquer sequência de caracteres não
    alfanuméricos por um único espaço.
    """

    decomposed = unicodedata.normalize("NFKD", text.casefold())
    without_accents = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    return _NON_ALNUM.sub(" ", without_accents).strip()


@dataclass(frozen=True, slots=True)
class TagDefinition:
    """Definição de uma tag do vocabulário."""

    tag: str
    label: str | None = None
    keywords: tuple[str, ...] = ()


@dataclass(frozen=True)
class Vocabulary:
    """Conjunto imutável de tags permitidas e seus sinônimos."""

    definitions: tuple[TagDefinition, ...]
    _by_tag: dict[str, TagDefinition] = field(
        init=False, repr=False, compare=False, default_factory=dict
    )

    def __post_init__(self) -> None:
        if not self.definitions:
            raise VocabularyError("O vocabulário não pode estar vazio")
        for definition in self.definitions:
            if not definition.tag:
                raise VocabularyError("Tag vazia no vocabulário")
            if definition.tag in self._by_tag:
                raise VocabularyError(f"Tag duplicada no vocabulário: {definition.tag}")
            self._by_tag[definition.tag] = definition

    @property
    def tags(self) -> frozenset[str]:
        return frozenset(self._by_tag)

    def __contains__(self, tag: object) -> bool:
        return tag in self._by_tag

    def __len__(self) -> int:
        return len(self._by_tag)

    def get(self, tag: str) -> TagDefinition | None:
        return self._by_tag.get(tag)

    def as_list(self) -> list[TagDefinition]:
        return list(self.definitions)

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        keywords_path: str | Path | None = None,
    ) -> Vocabulary:
        """Carrega o vocabulário de um arquivo JSON e, opcionalmente, sinônimos."""

        tags = _load_tag_definitions(Path(path))
        if keywords_path is not None:
            tags = _merge_keywords(tags, Path(keywords_path))
        return cls(tuple(tags))


def _read_json(path: Path) -> Any:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise VocabularyError(f"Arquivo não encontrado: {path}") from exc
    except OSError as exc:
        raise VocabularyError(f"Falha ao ler {path}: {exc}") from exc

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise VocabularyError(f"JSON inválido em {path}: {exc}") from exc


def _load_tag_definitions(path: Path) -> list[TagDefinition]:
    data = _read_json(path)

    if isinstance(data, dict):
        items = data.get("tags")
    else:
        items = data

    if not isinstance(items, list):
        raise VocabularyError(
            f"{path}: esperado uma lista de tags ou um objeto com a chave 'tags'"
        )

    definitions: list[TagDefinition] = []
    for index, item in enumerate(items):
        if isinstance(item, str):
            tag = item.strip()
            label: str | None = None
            keywords: tuple[str, ...] = ()
        elif isinstance(item, dict):
            tag = str(item.get("tag", "")).strip()
            label_value = item.get("label")
            label = str(label_value).strip() if label_value is not None else None
            keywords_value = item.get("keywords", [])
            if not isinstance(keywords_value, list) or not all(
                isinstance(keyword, str) for keyword in keywords_value
            ):
                raise VocabularyError(
                    f"{path}: 'keywords' da tag #{index} deve ser uma lista de strings"
                )
            keywords = tuple(
                keyword.strip() for keyword in keywords_value if keyword.strip()
            )
        else:
            raise VocabularyError(f"{path}: item #{index} de tags é inválido")

        if not tag:
            raise VocabularyError(f"{path}: tag vazia no item #{index}")
        definitions.append(TagDefinition(tag=tag, label=label, keywords=keywords))

    if not definitions:
        raise VocabularyError(f"{path}: o vocabulário está vazio")

    return definitions


def _merge_keywords(
    definitions: list[TagDefinition], keywords_path: Path
) -> list[TagDefinition]:
    data = _read_json(keywords_path)

    if not isinstance(data, dict):
        raise VocabularyError(
            f"{keywords_path}: esperado um objeto JSON mapeando tag para sinônimos"
        )

    mapping = data.get("keywords", data)
    if not isinstance(mapping, dict):
        raise VocabularyError(f"{keywords_path}: 'keywords' deve ser um objeto JSON")

    known = {definition.tag for definition in definitions}
    for tag in mapping:
        if tag.startswith("_"):
            continue
        if tag not in known:
            logger.warning(
                "Sinônimos ignorados para tag fora do vocabulário: %s", tag
            )

    merged: list[TagDefinition] = []
    for definition in definitions:
        extra = mapping.get(definition.tag, [])
        if not isinstance(extra, list) or not all(isinstance(item, str) for item in extra):
            raise VocabularyError(
                f"{keywords_path}: sinônimos de '{definition.tag}' devem ser uma lista"
            )
        combined = [*definition.keywords]
        for keyword in extra:
            cleaned = keyword.strip()
            if cleaned and cleaned not in combined:
                combined.append(cleaned)
        merged.append(
            TagDefinition(
                tag=definition.tag,
                label=definition.label,
                keywords=tuple(combined),
            )
        )

    return merged


__all__ = ["TagDefinition", "Vocabulary", "normalize_text"]
