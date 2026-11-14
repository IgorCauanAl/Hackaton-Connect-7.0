"""Controle de acesso por perfil (BO-RF-12). Autenticação real fica fora da demo."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.core.errors import AcessoNegado


class Perfil(str, Enum):
    LOJISTA = "lojista"
    STARTUP = "startup"
    ADMIN = "admin"
    MCP = "mcp"  # servidor MCP: somente leitura


@dataclass(frozen=True)
class Ator:
    perfil: Perfil
    id: int | None = None

    def exige(self, *perfis: Perfil) -> None:
        if self.perfil not in perfis:
            raise AcessoNegado(f"Perfil '{self.perfil.value}' não pode executar esta operação.")

    def exige_dono(self, perfil: Perfil, recurso_id: int | None) -> None:
        """Admin passa; o perfil indicado só acessa o próprio recurso."""
        if self.perfil is Perfil.ADMIN:
            return
        if self.perfil is not perfil or self.id != recurso_id:
            raise AcessoNegado("Você só pode acessar os seus próprios dados.")
