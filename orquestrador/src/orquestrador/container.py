"""Composition root do orquestrador (DI manual)."""

from __future__ import annotations

from dataclasses import dataclass

from orquestrador.services.demandas import ServicoDemandas
from orquestrador.services.insights import ServicoInsights
from orquestrador.services.mcp import ServicoMCP
from orquestrador.services.relatorios import ServicoRelatorios
from orquestrador.services.testes import ServicoTestes


@dataclass(frozen=True, slots=True)
class Container:
    demandas: ServicoDemandas
    insights: ServicoInsights
    testes: ServicoTestes
    relatorios: ServicoRelatorios
    mcp: ServicoMCP


__all__ = ["Container"]
