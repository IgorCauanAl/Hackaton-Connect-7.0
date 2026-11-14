"""Dependências do FastAPI: ator (headers) e container de serviços."""

from __future__ import annotations

from fastapi import Header, HTTPException, Request

from orquestrador.container import Container
from orquestrador.domain import PERFIS, Ator


def get_ator(
    x_perfil: str = Header(..., description="lojista | startup | admin | mcp"),
    x_ator_id: int | None = Header(
        None, description="id do lojista/startup (opcional)"
    ),
) -> Ator:
    """Lê o ator. A autorização real continua no backend operacional."""

    perfil = x_perfil.strip().lower()
    if perfil not in PERFIS:
        raise HTTPException(status_code=401, detail="Perfil inválido.")
    if x_ator_id is not None and x_ator_id <= 0:
        raise HTTPException(status_code=422, detail="X-Ator-Id inválido.")
    return Ator(perfil=perfil, id=x_ator_id)


def get_container(request: Request) -> Container:
    return request.app.state.container


__all__ = ["get_ator", "get_container"]
