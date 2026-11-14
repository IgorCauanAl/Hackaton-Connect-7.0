"""ORQ-RF-04 — ciclo de teste demonstrativo.

O orquestrador valida a autorização antes de chamar o backend, registra o teste,
confirma o status e garante que o feedback retornado pertence ao teste pedido.
"""

from __future__ import annotations

from typing import Any

from orquestrador.clients.backend import BackendClient
from orquestrador.domain import Ator
from orquestrador.errors import AcessoNegado, ErroDeValidacao, RespostaInvalida
from orquestrador.trilha import Trilha, etapa


class ServicoTestes:
    def __init__(self, backend: BackendClient) -> None:
        self._backend = backend

    async def solicitar(self, ator: Ator, dados: Any) -> dict[str, Any]:
        if ator.perfil != "lojista":
            raise AcessoNegado(
                "Somente o lojista pode solicitar um teste.",
                etapa="autorizacao",
            )
        if not dados.autorizacao:
            raise ErroDeValidacao(
                "É necessária a autorização expressa do lojista para solicitar o teste.",
                etapa="autorizacao",
            )

        trilha = Trilha()

        with etapa(trilha, "registro_teste"):
            registro = await self._backend.post(
                "/api/testes",
                ator=ator,
                json_body=dados.model_dump(mode="json"),
                etapa="registro_teste",
            )

        self._validar_registro(registro)
        teste_id = registro["teste_id"]

        with etapa(trilha, "confirmacao_status"):
            teste = await self._backend.get(
                f"/api/testes/{teste_id}",
                ator=ator,
                etapa="confirmacao_status",
            )

        if not isinstance(teste, dict):
            raise RespostaInvalida(
                "Consulta do teste retornou um payload inesperado.",
                etapa="confirmacao_status",
            )
        if teste.get("id") != teste_id:
            raise RespostaInvalida(
                "O teste retornado não corresponde ao teste registrado.",
                etapa="confirmacao_status",
            )
        if teste.get("status") != registro["teste_status"]:
            trilha.aviso(
                "status_divergente",
                "O status consultado divergiu do status retornado no registro.",
            )

        return {"resultado": registro, "teste": teste, "orquestracao": trilha.como_dict()}

    async def obter(self, ator: Ator, teste_id: int) -> dict[str, Any]:
        trilha = Trilha()

        with etapa(trilha, "consulta_teste"):
            teste = await self._backend.get(
                f"/api/testes/{teste_id}",
                ator=ator,
                etapa="consulta_teste",
            )

        if not isinstance(teste, dict) or teste.get("id") != teste_id:
            raise RespostaInvalida(
                "Consulta do teste retornou um payload inesperado.",
                etapa="consulta_teste",
            )
        return {"resultado": teste, "orquestracao": trilha.como_dict()}

    async def feedback(self, ator: Ator, teste_id: int) -> dict[str, Any]:
        trilha = Trilha()

        with etapa(trilha, "feedback_demo"):
            feedback = await self._backend.post(
                f"/api/testes/{teste_id}/feedback-demo",
                ator=ator,
                etapa="feedback_demo",
            )

        if not isinstance(feedback, dict):
            raise RespostaInvalida(
                "Feedback retornou um payload inesperado.", etapa="feedback_demo"
            )
        try:
            associado = int(feedback.get("teste_id"))
        except (TypeError, ValueError):
            associado = -1
        if associado != teste_id:
            raise RespostaInvalida(
                "O feedback retornado não pertence ao teste solicitado.",
                etapa="feedback_demo",
            )

        return {"resultado": feedback, "orquestracao": trilha.como_dict()}

    # --------------------------------------------------------------- helpers
    @staticmethod
    def _validar_registro(registro: Any) -> None:
        if not isinstance(registro, dict):
            raise RespostaInvalida(
                "Registro de teste retornou um payload inesperado.",
                etapa="registro_teste",
            )
        if not isinstance(registro.get("teste_id"), int):
            raise RespostaInvalida(
                "Registro de teste sem 'teste_id' inteiro.",
                etapa="registro_teste",
            )
        if not isinstance(registro.get("teste_status"), str):
            raise RespostaInvalida(
                "Registro de teste sem 'teste_status'.",
                etapa="registro_teste",
            )


__all__ = ["ServicoTestes"]
