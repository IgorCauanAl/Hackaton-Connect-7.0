"""Cliente HTTP somente leitura da API do backend operacional.

O cliente não conhece o schema das respostas: ele devolve o JSON exatamente
como recebido (pass-through). Apenas as rotas contratuais são chamadas.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ia_mcp.errors import BackendUnavailableError, ConfigurationError

logger = logging.getLogger(__name__)

RADAR_PATH = "api/mcp/radar"
STARTUPS_PATH = "api/mcp/startups"


class BackendClient:
    """Consome ``/api/mcp/radar`` e ``/api/mcp/startups`` por GET."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not base_url or not base_url.strip():
            raise ConfigurationError("IA_MCP_BACKEND_BASE_URL não configurada")
        self._base_url = base_url.strip().rstrip("/") + "/"
        self._timeout = timeout
        self._transport = transport

    async def _get(
        self, path: str, params: dict[str, str] | None = None
    ) -> Any:
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                response = await client.get(path, params=params)
        except httpx.TimeoutException as exc:
            raise BackendUnavailableError(
                f"Timeout ao consultar o backend em '{path}'"
            ) from exc
        except httpx.HTTPError as exc:
            raise BackendUnavailableError(
                f"Falha de comunicação com o backend em '{path}': {exc}"
            ) from exc

        if response.status_code >= 400:
            raise BackendUnavailableError(
                f"Backend respondeu HTTP {response.status_code} em '{path}'"
            )

        try:
            return response.json()
        except ValueError as exc:
            raise BackendUnavailableError(
                f"Backend retornou JSON inválido em '{path}'"
            ) from exc

    async def listar_radar(self) -> Any:
        """Retorna o payload de ``GET /api/mcp/radar`` sem alterações."""

        return await self._get(RADAR_PATH)

    async def buscar_startups(
        self,
        *,
        tag: str | None = None,
        segmento: str | None = None,
    ) -> Any:
        """Retorna o payload de ``GET /api/mcp/startups`` sem alterações."""

        params: dict[str, str] = {}
        if tag and tag.strip():
            params["tag"] = tag.strip()
        if segmento and segmento.strip():
            params["segmento"] = segmento.strip()

        return await self._get(STARTUPS_PATH, params or None)


__all__ = ["BackendClient", "RADAR_PATH", "STARTUPS_PATH"]
