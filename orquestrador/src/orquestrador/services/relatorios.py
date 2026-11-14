"""ORQ-RF-05 — encaminhamento de oportunidades e relatórios.

Sequência: valida ator/destinatário, encaminha no backend (que gera e persiste o
relatório), confirma a oportunidade na startup e só então disponibiliza o
documento. Cada vínculo demanda ↔ startup ↔ relatório é conferido.
"""

from __future__ import annotations

from typing import Any

from orquestrador.clients.backend import BackendClient
from orquestrador.domain import Ator
from orquestrador.errors import AcessoNegado, RequisicaoInvalida, RespostaInvalida
from orquestrador.trilha import Trilha, etapa

VERSOES = ("anonimizada", "completa")


class ServicoRelatorios:
    def __init__(self, backend: BackendClient) -> None:
        self._backend = backend

    async def encaminhar(
        self, ator: Ator, demanda_id: int, dados: Any
    ) -> dict[str, Any]:
        if ator.perfil != "admin":
            raise AcessoNegado(
                "Somente a associação (perfil admin) pode encaminhar oportunidades.",
                etapa="autorizacao",
            )

        trilha = Trilha()

        with etapa(trilha, "encaminhamento"):
            registro = await self._backend.post(
                f"/api/admin/demandas/{demanda_id}/encaminhar",
                ator=ator,
                json_body={"startup_id": dados.startup_id},
                etapa="encaminhamento",
            )

        if not isinstance(registro, dict) or not isinstance(
            registro.get("relatorio_id"), int
        ):
            raise RespostaInvalida(
                "Encaminhamento sem 'relatorio_id' inteiro.",
                etapa="encaminhamento",
            )
        relatorio_id = registro["relatorio_id"]

        with etapa(trilha, "confirmacao_oportunidade"):
            oportunidades = await self._backend.get(
                f"/api/startups/{dados.startup_id}/oportunidades",
                ator=ator,
                etapa="confirmacao_oportunidade",
            )

        if not isinstance(oportunidades, list):
            raise RespostaInvalida(
                "Lista de oportunidades retornou um payload inesperado.",
                etapa="confirmacao_oportunidade",
            )
        ids = {
            item.get("relatorio_id")
            for item in oportunidades
            if isinstance(item, dict)
        }
        if relatorio_id not in ids:
            trilha.aviso(
                "relatorio_nao_listado",
                "O relatório não apareceu na lista de oportunidades da startup.",
            )

        with etapa(trilha, "leitura_relatorio"):
            documento = await self._backend.get(
                f"/api/relatorios/{relatorio_id}",
                ator=ator,
                params={"versao": "anonimizada"},
                etapa="leitura_relatorio",
            )

        if not isinstance(documento, dict):
            raise RespostaInvalida(
                "Leitura do relatório retornou um payload inesperado.",
                etapa="leitura_relatorio",
            )
        if documento.get("demanda_id") != demanda_id:
            raise RespostaInvalida(
                "O relatório não corresponde à demanda encaminhada.",
                etapa="leitura_relatorio",
            )
        if documento.get("startup_id") != dados.startup_id:
            raise RespostaInvalida(
                "O relatório não corresponde à startup destinatária.",
                etapa="leitura_relatorio",
            )

        resultado = {
            **registro,
            "startup_id": dados.startup_id,
            "relatorio": documento,
        }
        return {"resultado": resultado, "orquestracao": trilha.como_dict()}

    async def listar_da_startup(
        self, ator: Ator, startup_id: int
    ) -> dict[str, Any]:
        trilha = Trilha()

        with etapa(trilha, "consulta_oportunidades"):
            dados = await self._backend.get(
                f"/api/startups/{startup_id}/oportunidades",
                ator=ator,
                etapa="consulta_oportunidades",
            )

        if not isinstance(dados, list):
            raise RespostaInvalida(
                "Lista de oportunidades retornou um payload inesperado.",
                etapa="consulta_oportunidades",
            )
        return {"resultado": dados, "orquestracao": trilha.como_dict()}

    async def ver(
        self, ator: Ator, relatorio_id: int, versao: str = "anonimizada"
    ) -> dict[str, Any]:
        if versao not in VERSOES:
            raise RequisicaoInvalida(
                "Versão inválida: use 'anonimizada' ou 'completa'.",
                etapa="validacao",
            )

        trilha = Trilha()

        with etapa(trilha, "leitura_relatorio"):
            documento = await self._backend.get(
                f"/api/relatorios/{relatorio_id}",
                ator=ator,
                params={"versao": versao},
                etapa="leitura_relatorio",
            )

        if not isinstance(documento, dict):
            raise RespostaInvalida(
                "Leitura do relatório retornou um payload inesperado.",
                etapa="leitura_relatorio",
            )
        return {"resultado": documento, "orquestracao": trilha.como_dict()}


__all__ = ["ServicoRelatorios", "VERSOES"]
