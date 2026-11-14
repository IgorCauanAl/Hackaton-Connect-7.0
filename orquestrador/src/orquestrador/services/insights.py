"""ORQ-RF-03 — geração de insights e Radar.

A IA só interpreta. Quantidades, pontuação, persistência e fallback de
referência continuam no backend; o orquestrador valida o contrato e garante que
apenas o perfil ``admin`` dispare a geração.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from orquestrador.clients.backend import BackendClient
from orquestrador.domain import Ator
from orquestrador.errors import AcessoNegado, ErroDeOrquestracao, RespostaInvalida
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

    async def padroes(self, ator: Ator) -> dict[str, Any]:
        """Radar + tag do grupo, derivada das demandas reais do backend.

        O backend ainda não expõe a tag no payload do radar. Em vez de alterar o
        contrato do backend, o orquestrador lê as demandas do grupo e escolhe a
        tag mais frequente entre elas — sem calcular quantidade, pontuação ou
        qualquer regra de matching.
        """

        self._exigir_admin(ator, "analisar os padrões")
        trilha = Trilha()

        with etapa(trilha, "consulta_radar"):
            dados = await self._backend.get(
                "/api/admin/radar",
                ator=ator,
                etapa="consulta_radar",
            )

        self._validar_radar(dados, etapa="consulta_radar")

        grupos_sem_tag = 0
        for item in dados["radar"]:
            item["tag"] = await self._tag_do_grupo(
                ator, item["grupo_id"], trilha
            )
            if item["tag"] is None:
                grupos_sem_tag += 1

        if grupos_sem_tag:
            trilha.aviso(
                "tag_grupo_indisponivel",
                f"{grupos_sem_tag} grupo(s) sem tag derivável; a consulta MCP "
                "fica limitada a esses padrões.",
            )

        return {"resultado": dados, "orquestracao": trilha.como_dict()}

    async def _tag_do_grupo(
        self, ator: Ator, grupo_id: int, trilha: Trilha
    ) -> str | None:
        """Tag dominante entre as demandas do grupo (máximo de 5 amostras)."""

        try:
            demandas = await self._backend.get(
                f"/api/admin/radar/{grupo_id}/demandas",
                ator=ator,
                etapa="padroes_grupo",
            )
        except ErroDeOrquestracao:
            return None

        if not isinstance(demandas, list):
            return None

        contagem: Counter[str] = Counter()
        for demanda in demandas[:5]:
            if not isinstance(demanda, dict) or not isinstance(
                demanda.get("id"), int
            ):
                continue
            try:
                detalhe = await self._backend.get(
                    f"/api/admin/demandas/{demanda['id']}",
                    ator=ator,
                    etapa="padroes_demanda",
                )
            except ErroDeOrquestracao:
                continue
            tags = detalhe.get("tags") if isinstance(detalhe, dict) else None
            if isinstance(tags, list):
                for tag in tags:
                    if isinstance(tag, str) and tag.strip():
                        contagem[tag.strip()] += 1

        return contagem.most_common(1)[0][0] if contagem else None

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
