"""Modelos internos do módulo.

Estes modelos são usados pelos serviços e logs internos. O contrato público
HTTP expõe apenas os campos exigidos pelo ``IAGateway`` (``tags``, ``resumo`` e
``interpretacoes``).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ClassificationOutcome(BaseModel):
    """Resultado interno de uma classificação."""

    tags: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    provider: str
    fallback_used: bool = False


class SummaryOutcome(BaseModel):
    """Resultado interno de um resumo."""

    resumo: str
    provider: str
    fallback_used: bool = False


class InsightsOutcome(BaseModel):
    """Resultado interno de uma interpretação de grupos."""

    interpretacoes: dict[str, str] = Field(default_factory=dict)
    provider: str
    fallback_used: bool = False


class DemandaInsight(BaseModel):
    """Demanda recebida dentro de um grupo para interpretação."""

    id: str = Field(min_length=1)
    texto: str


class GrupoInsight(BaseModel):
    """Grupo de demandas enviado pelo orquestrador/backend."""

    id: str = Field(min_length=1)
    titulo: str | None = None
    tags: list[str] = Field(default_factory=list)
    demandas: list[DemandaInsight] = Field(default_factory=list)


__all__ = [
    "ClassificationOutcome",
    "DemandaInsight",
    "GrupoInsight",
    "InsightsOutcome",
    "SummaryOutcome",
]
