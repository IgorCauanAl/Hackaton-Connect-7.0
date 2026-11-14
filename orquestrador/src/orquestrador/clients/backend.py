"""Cliente HTTP do backend operacional.

Propaga o ator (``X-Perfil``/``X-Ator-Id``) e traduz qualquer falha para os
erros controlados do orquestrador. Não conhece regra de negócio.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from orquestrador.domain import Ator
from orquestrador.errors import (
    ErroDeOrquestracao,
    FalhaNoBackend,
    RespostaInvalida,
    ServicoIndisponivel,
)

_CODIGOS_4XX = {
    401: "ator_invalido",
    403: "acesso_negado",
    404: "nao_encontrado",
    409: "regra_de_negocio",
    422: "requisicao_invalida",
}


def _detalhe_da_resposta(resposta: httpx.Response) -> str | None:
    try:
        corpo = resposta.json()
    except ValueError:
        return None
    if not isinstance(corpo, dict):
        return None
    detalhe = corpo.get("detail")
    if isinstance(detalhe, str) and detalhe.strip():
        return detalhe.strip()
    if detalhe is not None:
        return json.dumps(detalhe, ensure_ascii=False)
    return None


class BackendClient:
    """Acesso HTTP à API do backend operacional."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not base_url or not base_url.strip():
            raise ValueError("ORQ_BACKEND_BASE_URL não configurada")
        self._base_url = base_url.strip().rstrip("/") + "/"
        self._timeout = timeout
        self._transport = transport

    async def _request(
        self,
        metodo: str,
        caminho: str,
        *,
        ator: Ator,
        json_body: Any = None,
        params: dict[str, str] | None = None,
        etapa: str = "backend",
    ) -> Any:
        headers = {"X-Perfil": ator.perfil}
        if ator.id is not None:
            headers["X-Ator-Id"] = str(ator.id)

        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                resposta = await client.request(
                    metodo,
                    caminho.lstrip("/"),
                    json=json_body,
                    params=params,
                    headers=headers,
                )
        except httpx.TimeoutException as exc:
            raise ServicoIndisponivel(
                f"Timeout ao chamar o backend em '{caminho}'.",
                etapa=etapa,
                codigo="backend_timeout",
            ) from exc
        except httpx.HTTPError as exc:
            raise FalhaNoBackend(
                f"Falha de comunicação com o backend em '{caminho}': {exc}",
                etapa=etapa,
            ) from exc

        if resposta.status_code >= 500:
            raise FalhaNoBackend(
                f"Backend respondeu HTTP {resposta.status_code} em '{caminho}'.",
                etapa=etapa,
            )

        if resposta.status_code >= 400:
            detalhe = _detalhe_da_resposta(resposta)
            raise ErroDeOrquestracao(
                detalhe
                or f"Backend respondeu HTTP {resposta.status_code} em '{caminho}'.",
                etapa=etapa,
                codigo=_CODIGOS_4XX.get(resposta.status_code, "requisicao_invalida"),
                status=resposta.status_code,
            )

        try:
            return resposta.json()
        except ValueError as exc:
            raise RespostaInvalida(
                f"Backend retornou JSON inválido em '{caminho}'.",
                etapa=etapa,
            ) from exc

    async def get(
        self,
        caminho: str,
        *,
        ator: Ator,
        params: dict[str, str] | None = None,
        etapa: str = "backend",
    ) -> Any:
        return await self._request(
            "GET", caminho, ator=ator, params=params, etapa=etapa
        )

    async def post(
        self,
        caminho: str,
        *,
        ator: Ator,
        json_body: Any = None,
        etapa: str = "backend",
    ) -> Any:
        return await self._request(
            "POST", caminho, ator=ator, json_body=json_body, etapa=etapa
        )


__all__ = ["BackendClient"]
