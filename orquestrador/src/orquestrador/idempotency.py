"""Idempotência de POSTs: evita duplicar operações (ORQ-RF-06).

O armazenamento é em memória, com TTL. Para a demo em processo único isso é
suficiente; a interface permite trocar por Redis sem tocar nas rotas.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from time import monotonic
from typing import Any, Awaitable, Callable

from fastapi import Request
from fastapi.responses import JSONResponse

from orquestrador.errors import ErroDeValidacao


def fingerprint(*partes: Any) -> str:
    """Hash estável do escopo da requisição (rota, ator e corpo)."""

    serializado = json.dumps(partes, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(serializado.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class EntradaIdempotente:
    fingerprint: str
    status: int
    corpo: Any


class IdempotencyStore:
    def __init__(self, ttl_seconds: float = 600.0) -> None:
        self._ttl = ttl_seconds
        self._itens: dict[str, tuple[EntradaIdempotente, float]] = {}

    def _purgar(self, agora: float) -> None:
        expirados = [
            chave
            for chave, (_, expira_em) in self._itens.items()
            if expira_em <= agora
        ]
        for chave in expirados:
            del self._itens[chave]

    def obter(self, chave: str, digital: str) -> EntradaIdempotente | None:
        agora = monotonic()
        self._purgar(agora)
        registro = self._itens.get(chave)
        if registro is None:
            return None
        entrada, _ = registro
        if entrada.fingerprint != digital:
            raise ErroDeValidacao(
                "A mesma Idempotency-Key foi reutilizada com um corpo diferente.",
                etapa="idempotencia",
                codigo="idempotency_conflict",
            )
        return entrada

    def salvar(
        self, chave: str, digital: str, status: int, corpo: Any
    ) -> None:
        self._itens[chave] = (
            EntradaIdempotente(fingerprint=digital, status=status, corpo=corpo),
            monotonic() + self._ttl,
        )

    def limpar(self) -> None:
        self._itens.clear()


async def executar_idempotente(
    request: Request,
    corpo: Any,
    acao: Callable[[], Awaitable[tuple[Any, int]]],
) -> JSONResponse:
    """Executa ``acao`` uma única vez por ``Idempotency-Key``.

    A chave é opcional. Quando ausente, a operação segue o fluxo normal.
    """

    chave = request.headers.get("Idempotency-Key")
    if not chave:
        resposta, status = await acao()
        return JSONResponse(resposta, status_code=status)

    store: IdempotencyStore = request.app.state.idempotencia
    digital = fingerprint(
        request.method,
        request.url.path,
        request.headers.get("x-perfil"),
        request.headers.get("x-ator-id"),
        corpo.model_dump(mode="json") if hasattr(corpo, "model_dump") else corpo,
    )

    entrada = store.obter(chave, digital)
    if entrada is not None:
        return JSONResponse(
            entrada.corpo,
            status_code=entrada.status,
            headers={"X-Idempotente-Replay": "true"},
        )

    resposta, status = await acao()
    store.salvar(chave, digital, status, resposta)
    return JSONResponse(resposta, status_code=status)


__all__ = ["EntradaIdempotente", "IdempotencyStore", "executar_idempotente", "fingerprint"]
