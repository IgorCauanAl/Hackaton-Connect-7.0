"""Modelos de domínio do orquestrador."""

from __future__ import annotations

from dataclasses import dataclass

PERFIS = ("lojista", "startup", "admin", "mcp")


@dataclass(frozen=True, slots=True)
class Ator:
    """Ator repassado ao backend operacional.

    O orquestrador NÃO autentica: apenas propaga ``X-Perfil``/``X-Ator-Id``. A
    decisão de acesso continua sendo do backend.
    """

    perfil: str
    id: int | None = None


__all__ = ["Ator", "PERFIS"]
