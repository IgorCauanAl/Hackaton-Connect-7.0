"""Ponto de entrada: uvicorn app.main:app --reload"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import seed
from app.api import routes_admin, routes_lojista, routes_startup
from app.api.deps import get_settings
from app.core.errors import ErroDeDominio
from app.infra import database


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    conn = database.connect(settings.db_path)
    try:
        database.init_schema(conn)
        if conn.execute("SELECT COUNT(*) FROM lojistas").fetchone()[0] == 0:
            seed.carregar(conn, settings)  # primeira subida: banco da demo pronto
    finally:
        conn.close()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="FACESP Match — Backend operacional", version="0.1.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://localhost:3000"],
                       allow_methods=["*"], allow_headers=["*"])

    @app.exception_handler(ErroDeDominio)
    async def erro_dominio(_: Request, exc: ErroDeDominio):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.mensagem})

    for router in (routes_lojista.router, routes_startup.router, routes_admin.router):
        app.include_router(router)

    @app.get("/api/saude", tags=["infra"])
    def saude():
        return {"status": "ok"}

    return app


app = create_app()
