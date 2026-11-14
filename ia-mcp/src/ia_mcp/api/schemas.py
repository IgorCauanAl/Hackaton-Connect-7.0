"""Contratos HTTP públicos exigidos pelo ``IAGateway`` do backend.

As respostas de sucesso contêm **somente** os campos abaixo. Metadados como
provedor, confiança e fallback permanecem internos.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from ia_mcp.domain.models import GrupoInsight


class ClassificarRequest(BaseModel):
    texto: str = Field(min_length=1)

    @field_validator("texto")
    @classmethod
    def _texto_obrigatorio(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("O texto não pode ser vazio")
        return stripped


class ClassificarResponse(BaseModel):
    tags: list[str]


class ResumirRequest(BaseModel):
    texto: str = Field(min_length=1)

    @field_validator("texto")
    @classmethod
    def _texto_obrigatorio(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("O texto não pode ser vazio")
        return stripped


class ResumirResponse(BaseModel):
    resumo: str


class InsightsRequest(BaseModel):
    grupos: list[GrupoInsight]


class InsightsResponse(BaseModel):
    interpretacoes: dict[str, str]


__all__ = [
    "ClassificarRequest",
    "ClassificarResponse",
    "InsightsRequest",
    "InsightsResponse",
    "ResumirRequest",
    "ResumirResponse",
]
