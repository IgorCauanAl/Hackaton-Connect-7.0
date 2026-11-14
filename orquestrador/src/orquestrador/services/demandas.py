"""ORQ-RF-01/02 — demandas e matching.

O orquestrador executa a sequência:

1. recebe o resultado do chat;
2. chama a IA para classificar o texto livre;
3. se a IA falhar, segue sem tags e o backend aplica o fallback por botões;
4. registra a demanda no backend (que calcula e persiste o matching);
5. valida o contrato da resposta antes de devolver.
"""

from __future__ import annotations

from typing import Any

from orquestrador.clients.backend import BackendClient
from orquestrador.clients.ia import IAClient
from orquestrador.domain import Ator
from orquestrador.errors import IAIndisponivel, RespostaInvalida
from orquestrador.trilha import Trilha, etapa


class ServicoDemandas:
    def __init__(self, backend: BackendClient, ia: IAClient) -> None:
        self._backend = backend
        self._ia = ia

    async def registrar(self, ator: Ator, dados: Any) -> dict[str, Any]:
        trilha = Trilha()
        tags = await self._classificar(dados.texto_livre, trilha)

        corpo = {
            "lojista_id": dados.lojista_id,
            "respostas": dados.respostas.model_dump(mode="json"),
            "texto_livre": dados.texto_livre,
        }
        if tags:
            corpo["tags"] = tags

        with etapa(trilha, "registro_demanda"):
            resultado = await self._backend.post(
                "/api/demandas",
                ator=ator,
                json_body=corpo,
                etapa="registro_demanda",
            )

        self._validar_registro(resultado)
        if resultado["status"] == "sem_match":
            trilha.aviso(
                "sem_match",
                "Nenhuma solução compatível; a demanda foi encaminhada à curadoria.",
            )

        return {"resultado": resultado, "orquestracao": trilha.como_dict()}

    async def matching(self, ator: Ator, demanda_id: int) -> dict[str, Any]:
        trilha = Trilha()

        with etapa(trilha, "consulta_matching"):
            dados = await self._backend.get(
                f"/api/demandas/{demanda_id}/matching",
                ator=ator,
                etapa="consulta_matching",
            )

        if not isinstance(dados, dict):
            raise RespostaInvalida(
                "Matching retornou um payload inesperado.",
                etapa="consulta_matching",
            )
        if not isinstance(dados.get("ranking_startups"), list):
            raise RespostaInvalida(
                "Matching sem a lista 'ranking_startups'.",
                etapa="consulta_matching",
            )
        if not isinstance(dados.get("sem_match"), bool):
            raise RespostaInvalida(
                "Matching sem o campo booleano 'sem_match'.",
                etapa="consulta_matching",
            )
        if dados["sem_match"] and dados["ranking_startups"]:
            trilha.aviso(
                "matching_inconsistente",
                "O backend sinalizou sem_match, mas retornou ranking.",
            )

        return {"resultado": dados, "orquestracao": trilha.como_dict()}

    async def validar(self, ator: Ator, demanda_id: int) -> dict[str, Any]:
        """Encaminha a validação da curadoria ao backend (perfil admin)."""

        trilha = Trilha()

        with etapa(trilha, "validacao_demanda"):
            resultado = await self._backend.post(
                f"/api/admin/demandas/{demanda_id}/validar",
                ator=ator,
                etapa="validacao_demanda",
            )

        if not isinstance(resultado, dict) or resultado.get("status") not in (
            "validado",
            "validada",
        ):
            raise RespostaInvalida(
                "Validação retornou um payload inesperado.",
                etapa="validacao_demanda",
            )

        return {"resultado": resultado, "orquestracao": trilha.como_dict()}

    # --------------------------------------------------------------- helpers
    async def _classificar(
        self, texto: str, trilha: Trilha
    ) -> list[str] | None:
        try:
            with etapa(trilha, "classificacao_ia"):
                tags = await self._ia.classificar(texto)
        except IAIndisponivel as exc:
            trilha.aviso(
                "ia_indisponivel",
                "Classificação via IA indisponível "
                f"({exc}); o backend aplicará o fallback por botões.",
            )
            return None

        if not tags:
            trilha.aviso(
                "classificacao_vazia",
                "A IA não retornou tags; o backend aplicará o fallback por botões.",
            )
            return None

        return tags

    @staticmethod
    def _validar_registro(resultado: Any) -> None:
        if not isinstance(resultado, dict):
            raise RespostaInvalida(
                "Registro de demanda retornou um payload inesperado.",
                etapa="registro_demanda",
            )
        if not isinstance(resultado.get("demanda_id"), int):
            raise RespostaInvalida(
                "Registro de demanda sem 'demanda_id' inteiro.",
                etapa="registro_demanda",
            )
        if resultado.get("status") not in ("sucesso", "sem_match"):
            raise RespostaInvalida(
                "Registro de demanda com status inválido.",
                etapa="registro_demanda",
            )
        if not isinstance(resultado.get("tags_identificadas"), list):
            raise RespostaInvalida(
                "Registro de demanda sem 'tags_identificadas'.",
                etapa="registro_demanda",
            )
        if not isinstance(resultado.get("ranking_startups"), list):
            raise RespostaInvalida(
                "Registro de demanda sem 'ranking_startups'.",
                etapa="registro_demanda",
            )
        if resultado["status"] == "sucesso" and not resultado["ranking_startups"]:
            raise RespostaInvalida(
                "Registro indicou sucesso sem nenhuma startup no ranking.",
                etapa="registro_demanda",
            )


__all__ = ["ServicoDemandas"]
