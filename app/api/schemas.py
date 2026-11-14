"""Contratos de entrada da API (validação). Saídas são dicts já montados pelos serviços."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RespostasChat(BaseModel):
    objetivo: Literal["vender_mais", "reduzir_custos", "organizar_gestao", "fidelizar_clientes", "outro"]
    dificuldade: Literal["atrair_clientes", "atender_whatsapp", "vender_online", "trazer_cliente_de_volta",
                         "controle_estoque_caixa", "outro"]
    canais: list[Literal["loja", "whatsapp", "instagram", "site_proprio", "marketplace"]] = Field(min_length=1)
    ferramentas: list[Literal["nenhuma", "planilha", "sistema_caixa", "crm", "outra"]] = Field(min_length=1)
    orcamento: Literal["ate_100", "100_300", "300_800", "acima"]
    urgencia: Literal["ate_15_dias", "ate_2_meses", "sem_pressa"]


class DemandaIn(BaseModel):
    lojista_id: int
    respostas: RespostasChat
    texto_livre: str = Field(min_length=1, max_length=500)


class TesteIn(BaseModel):
    demanda_id: int
    startup_id: int
    autorizacao: bool


class EncaminharIn(BaseModel):
    startup_id: int
