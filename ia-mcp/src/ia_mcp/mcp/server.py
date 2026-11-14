"""Servidor FastMCP com ferramentas somente leitura sobre a API do backend."""

from __future__ import annotations

import logging

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from ia_mcp.backend.client import BackendClient
from ia_mcp.errors import BackendUnavailableError

logger = logging.getLogger(__name__)

_READ_ONLY = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True}


def create_mcp_server(backend_client: BackendClient) -> FastMCP:
    """Cria o servidor MCP com exatamente duas ferramentas de leitura."""

    mcp = FastMCP(
        name="ia-mcp-facesp",
        instructions=(
            "Ferramentas somente leitura para consultar o radar de oportunidades "
            "e as startups do FACESP Match. Nenhuma ferramenta escreve dados."
        ),
    )

    @mcp.tool(
        name="listar_radar",
        description="Lista as oportunidades do radar do backend FACESP Match.",
        annotations=_READ_ONLY,
        tags={"read-only"},
    )
    async def listar_radar():
        try:
            return await backend_client.listar_radar()
        except BackendUnavailableError as exc:
            logger.warning("Falha ao listar radar: %s", exc)
            raise ToolError(f"Não foi possível consultar o radar: {exc}") from exc

    @mcp.tool(
        name="buscar_startups",
        description=(
            "Busca startups no backend FACESP Match, opcionalmente filtrando por "
            "tag e segmento. É uma consulta de leitura, não um cálculo de matching."
        ),
        annotations=_READ_ONLY,
        tags={"read-only"},
    )
    async def buscar_startups(
        tag: str | None = None,
        segmento: str | None = None,
    ):
        try:
            return await backend_client.buscar_startups(tag=tag, segmento=segmento)
        except BackendUnavailableError as exc:
            logger.warning("Falha ao buscar startups: %s", exc)
            raise ToolError(f"Não foi possível consultar startups: {exc}") from exc

    return mcp


__all__ = ["create_mcp_server"]
