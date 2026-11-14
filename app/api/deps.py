"""Dependências do FastAPI: conexão por requisição, serviços e ator (perfil)."""
from __future__ import annotations

from functools import lru_cache
from typing import Iterator

from fastapi import Depends, Header, HTTPException

from app.container import Servicos, montar
from app.core.config import Settings
from app.core.security import Ator, Perfil
from app.infra import database


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()


def get_conn(settings: Settings = Depends(get_settings)) -> Iterator:
    conn = database.connect(settings.db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_servicos(conn=Depends(get_conn), settings: Settings = Depends(get_settings)) -> Servicos:
    return montar(conn, settings)


def get_ator(x_perfil: str = Header(..., description="lojista | startup | admin | mcp"),
             x_ator_id: int | None = Header(None, description="id do lojista/startup")) -> Ator:
    """Autenticação simplificada da demo: o front informa o perfil escolhido."""
    try:
        return Ator(Perfil(x_perfil.lower()), x_ator_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Perfil inválido.")
