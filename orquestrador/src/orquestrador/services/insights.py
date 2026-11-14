"""ORQ-RF-03 — geração de insights e Radar.

A IA só interpreta. Quantidades, pontuação, persistência e fallback de
referência continuam no backend; o orquestrador valida o contrato e garante que
apenas o perfil ``admin`` dispare a geração.
"""

from __future__ import annotations

from typing import Any

from orquestrador.clients.backend import BackendClient
from orquestrador.domain import Ator
from orquestrador.errors import AcessoNegado, RespostaInvalida
from orquestrador.trilha import Trilha, etapa

CAMPOS_RADAR = {
    "grupo_id",
    "titulo",
    "quantidade",
    "pontuacao",
    "sugestao",
    "origem",
    "destaque",
    "requer_validacao_humana",
}


class ServicoInsights:
    def __init__(self, backend: BackendClient) -> None:
        self._backend = backend

    async def gerar(self, ator: Ator) -> dict[str, Any]:
        self._exigir_admin(ator, "gerar insights")
        trilha = Trilha()

        with etapa(trilha, "geracao_insights"):
            dados = await self._backend.post(
                "/api/admin/insights/gerar",
                ator=ator,
                etapa="geracao_insights",
            )

        self._validar_radar(dados, etapa="geracao_insights")
        origens = {item.get("origem") for item in dados["radar"]}
        if "referencia" in origens:
            trilha.aviso(
                "fallback_referencia",
                "A IA não respondeu; o backend usou a interpretação de referência.",
            )

        return {"resultado": dados, "orquestracao": trilha.como_dict()}

    async def radar(self, ator: Ator) -> dict[str, Any]:
        self._exigir_admin(ator, "consultar o Radar")
        trilha = Trilha()

        with etapa(trilha, "consulta_radar"):
            dados = await self._backend.get(
                "/api/admin/radar",
                ator=ator,
                etapa="consulta_radar",
            )

        self._validar_radar(dados, etapa="consulta_radar")
        return {"resultado": dados, "orquestracao": trilha.como_dict()}

    # --------------------------------------------------------------- helpers
    @staticmethod
    def _exigir_admin(ator: Ator, acao: str) -> None:
        if ator.perfil != "admin":
            raise AcessoNegado(
                f"Somente a associação (perfil admin) pode {acao}.",
                etapa="autorizacao",
            )

    @staticmethod
    def _validar_radar(dados: Any, *, etapa: str) -> None:
        if not isinstance(dados, dict):
            raise RespostaInvalida(
                "Radar retornou um payload inesperado.", etapa=etapa
            )
        radar = dados.get("radar")
        if not isinstance(radar, list):
            raise RespostaInvalida(
                "Radar sem a lista 'radar'.", etapa=etapa
            )
        for item in radar:
            if not isinstance(item, dict):
                raise RespostaInvalida(
                    "Item do Radar não é um objeto.", etapa=etapa
                )
            faltando = CAMPOS_RADAR - set(item)
            if faltando:
                raise RespostaInvalida(
                    f"Item do Radar sem os campos: {sorted(faltando)}.",
                    etapa=etapa,
                )
            if not isinstance(item["quantidade"], int):
                raise RespostaInvalida(
                    "Item do Radar com 'quantidade' não inteira.", etapa=etapa
                )
            if not isinstance(item["sugestao"], str) or not item["sugestao"].strip():
                raise RespostaInvalida(
                    "Item do Radar sem 'sugestao' textual.", etapa=etapa
                )


__all__ = ["CAMPOS_RADAR", "ServicoInsights"]
