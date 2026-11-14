"""Cliente FastMCP do orquestrador.

O orquestrador consome as ferramentas **somente leitura** expostas pelo IA/MCP
(``listar_radar`` e ``buscar_startups``) por Streamable HTTP. Não existe
ferramenta de escrita e nenhuma fonte de dados paralela: o servidor MCP usa a
API real do backend operacional.
"""

from __future__ import annotations

import json
from typing import Any

from fastmcp import Client
from fastmcp.exceptions import McpError

from orquestrador.errors import ServicoIndisponivel


class MCPClient:
    """Executa ferramentas FastMCP e devolve o payload já desserializado."""

    def __init__(
        self,
        *,
        url: str,
        timeout: float = 10.0,
        client_factory=None,
    ) -> None:
        if not url or not url.strip():
            raise ValueError("ORQ_MCP_URL não configurada")
        self._url = url.strip()
        self._timeout = timeout
        self._client_factory = client_factory or self._default_factory

    def _default_factory(self, url: str, timeout: float) -> Client:
        return Client(url, timeout=timeout)

    async def chamar(
        self, ferramenta: str, argumentos: dict[str, Any] | None = None
    ) -> Any:
        etapa = f"mcp_{ferramenta}"
        try:
            async with self._client_factory(self._url, self._timeout) as client:
                resultado = await client.call_tool(
                    ferramenta, argumentos or {}, raise_on_error=False
                )
        except (McpError, OSError, TimeoutError) as exc:
            raise ServicoIndisponivel(
                f"Falha ao chamar a ferramenta MCP '{ferramenta}': {exc}",
                etapa=etapa,
                codigo="mcp_indisponivel",
            ) from exc
        except Exception as exc:  # noqa: BLE001 - transporte MCP tem vários erros
            raise ServicoIndisponivel(
                f"Falha ao chamar a ferramenta MCP '{ferramenta}': {exc}",
                etapa=etapa,
                codigo="mcp_indisponivel",
            ) from exc

        if getattr(resultado, "is_error", False):
            detalhe = _texto_do_resultado(resultado) or "erro não detalhado"
            raise ServicoIndisponivel(
                f"A ferramenta MCP '{ferramenta}' retornou erro: {detalhe}",
                etapa=etapa,
                codigo="mcp_indisponivel",
            )

        dados = getattr(resultado, "data", None)
        if dados is not None:
            return dados

        texto = _texto_do_resultado(resultado)
        if texto is None:
            raise ServicoIndisponivel(
                f"A ferramenta MCP '{ferramenta}' retornou um payload vazio.",
                etapa=etapa,
                codigo="mcp_indisponivel",
            )
        try:
            return json.loads(texto)
        except ValueError as exc:
            raise ServicoIndisponivel(
                f"A ferramenta MCP '{ferramenta}' retornou JSON inválido.",
                etapa=etapa,
                codigo="mcp_indisponivel",
            ) from exc


def _texto_do_resultado(resultado: Any) -> str | None:
    """Extrai o primeiro bloco textual do ``CallToolResult``."""

    for bloco in getattr(resultado, "content", None) or []:
        texto = getattr(bloco, "text", None)
        if isinstance(texto, str) and texto.strip():
            return texto
    return None


__all__ = ["MCPClient"]
