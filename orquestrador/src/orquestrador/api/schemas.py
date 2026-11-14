"""Contratos de entrada do orquestrador.

Espelham os schemas do backend operacional para falhar cedo (422) sem chamar
serviços externos.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Objetivo = Literal[
    "vender_mais",
    "reduzir_custos",
    "organizar_gestao",
    "fidelizar_clientes",
    "outro",
]
Dificuldade = Literal[
    "atrair_clientes",
    "atender_whatsapp",
    "vender_online",
    "trazer_cliente_de_volta",
    "controle_estoque_caixa",
    "outro",
]
Canal = Literal["loja", "whatsapp", "instagram", "site_proprio", "marketplace"]
Ferramenta = Literal["nenhuma", "planilha", "sistema_caixa", "crm", "outra"]
Orcamento = Literal["ate_100", "100_300", "300_800", "acima"]
Urgencia = Literal["ate_15_dias", "ate_2_meses", "sem_pressa"]


class RespostasChat(BaseModel):
    objetivo: Objetivo
    dificuldade: Dificuldade
    canais: list[Canal] = Field(min_length=1)
    ferramentas: list[Ferramenta] = Field(min_length=1)
    orcamento: Orcamento
    urgencia: Urgencia


class DemandaRequest(BaseModel):
    lojista_id: int = Field(gt=0)
    respostas: RespostasChat
    texto_livre: str = Field(min_length=1, max_length=500)


class TesteRequest(BaseModel):
    demanda_id: int = Field(gt=0)
    startup_id: int = Field(gt=0)
    autorizacao: bool


class EncaminharRequest(BaseModel):
    startup_id: int = Field(gt=0)


__all__ = [
    "DemandaRequest",
    "EncaminharRequest",
    "RespostasChat",
    "TesteRequest",
]
