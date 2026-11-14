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


class GrupoInsight(BaseModel):
    """Grupo de demandas no formato real enviado pelo backend operacional.

    Espelha o payload de ``RadarService.gerar_insights``:

    ``{"chave": str, "titulo": str | None, "quantidade": int, "exemplos": [str]}``

    A IA pode narrar o grupo, mas nunca devolver contagens, pesos, scores ou
    status: ``quantidade`` é apenas informação de contexto recebida.
    """

    chave: str = Field(min_length=1)
    titulo: str | None = None
    quantidade: int = Field(default=0, ge=0)
    exemplos: list[str] = Field(default_factory=list)


__all__ = [
    "ClassificationOutcome",
    "GrupoInsight",
    "InsightsOutcome",
    "SummaryOutcome",
]
