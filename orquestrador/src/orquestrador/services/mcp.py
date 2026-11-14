"""ORQ-RF-03 (complemento) — ferramentas MCP somente leitura.

O orquestrador não reimplementa as ferramentas: apenas chama o servidor FastMCP
do IA/MCP e valida o contrato. O servidor MCP, por sua vez, lê o backend real.
"""

from __future__ import annotations

from typing import Any

from orquestrador.clients.mcp import MCPClient
from orquestrador.domain import Ator
from orquestrador.errors import AcessoNegado, RespostaInvalida
from orquestrador.trilha import Trilha, etapa

CAMPOS_RADAR_MCP = {"dor", "quantidade", "sugestao_ia", "origem"}
CAMPOS_STARTUP_MCP = {"id", "nome", "descricao", "solucao", "segmentos", "tags"}


class ServicoMCP:
    def __init__(self, mcp: MCPClient) -> None:
        self._mcp = mcp

    async def radar(self, ator: Ator) -> dict[str, Any]:
        self._exigir_leitura(ator, "consultar o radar MCP")
        trilha = Trilha()

        with etapa(trilha, "mcp_radar"):
            dados = await self._mcp.chamar("listar_radar")

        self._validar_radar(dados, etapa="mcp_radar")
        return {"resultado": dados, "orquestracao": trilha.como_dict()}

    async def startups(self, ator: Ator, tag: str | None) -> dict[str, Any]:
        self._exigir_leitura(ator, "consultar startups no MCP")
        trilha = Trilha()

        argumentos = {"tag": tag} if tag else {}
        with etapa(trilha, "mcp_startups"):
            dados = await self._mcp.chamar("buscar_startups", argumentos)

        self._validar_startups(dados, etapa="mcp_startups")
        return {"resultado": dados, "orquestracao": trilha.como_dict()}

    # --------------------------------------------------------------- helpers
    @staticmethod
    def _exigir_leitura(ator: Ator, acao: str) -> None:
        if ator.perfil not in ("admin", "mcp"):
            raise AcessoNegado(
                f"Somente a associação (admin) ou o MCP podem {acao}.",
                etapa="autorizacao",
            )

    @staticmethod
    def _validar_radar(dados: Any, *, etapa: str) -> None:
        if not isinstance(dados, list):
            raise RespostaInvalida(
                "MCP listar_radar não retornou uma lista.", etapa=etapa
            )
        for item in dados:
            if not isinstance(item, dict) or CAMPOS_RADAR_MCP - set(item):
                raise RespostaInvalida(
                    "Item do radar MCP fora do contrato.", etapa=etapa
                )
            if not isinstance(item["quantidade"], int):
                raise RespostaInvalida(
                    "Item do radar MCP com 'quantidade' não inteira.",
                    etapa=etapa,
                )

    @staticmethod
    def _validar_startups(dados: Any, *, etapa: str) -> None:
        if not isinstance(dados, list):
            raise RespostaInvalida(
                "MCP buscar_startups não retornou uma lista.", etapa=etapa
            )
        for item in dados:
            if not isinstance(item, dict) or CAMPOS_STARTUP_MCP - set(item):
                raise RespostaInvalida(
                    "Startup retornada pelo MCP fora do contrato.", etapa=etapa
                )
            if not isinstance(item["id"], int):
                raise RespostaInvalida(
                    "Startup do MCP sem 'id' inteiro.", etapa=etapa
                )


__all__ = ["CAMPOS_RADAR_MCP", "CAMPOS_STARTUP_MCP", "ServicoMCP"]
