"""Cliente do serviço IA/MCP (classificação textual)."""

from __future__ import annotations

from typing import Any

import httpx

from orquestrador.errors import IAIndisponivel


class IAClient:
    """Chama ``POST /ia/classificar`` e valida o contrato mínimo ``{"tags": [...]}``."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout: float = 25.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not base_url or not base_url.strip():
            raise ValueError("ORQ_IA_BASE_URL não configurada")
        self._base_url = base_url.strip().rstrip("/") + "/"
        self._timeout = timeout
        self._transport = transport

    async def classificar(self, texto: str) -> list[str]:
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                resposta = await client.post(
                    "ia/classificar", json={"texto": texto}
                )
        except httpx.HTTPError as exc:
            raise IAIndisponivel(f"falha de comunicação: {exc}") from exc

        if resposta.status_code >= 400:
            raise IAIndisponivel(f"HTTP {resposta.status_code}")

        try:
            corpo: Any = resposta.json()
        except ValueError as exc:
            raise IAIndisponivel("JSON inválido") from exc

        if not isinstance(corpo, dict):
            raise IAIndisponivel("resposta não é um objeto JSON")

        tags = corpo.get("tags")
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            raise IAIndisponivel("campo 'tags' ausente ou inválido")

        return [tag.strip() for tag in tags if tag.strip()]


__all__ = ["IAClient"]
