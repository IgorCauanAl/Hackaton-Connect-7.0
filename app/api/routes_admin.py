from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_ator, get_servicos
from app.api.schemas import EncaminharIn
from app.container import Servicos
from app.core.security import Ator

router = APIRouter(prefix="/api", tags=["associação"])


@router.get("/admin/dashboard")
def dashboard(ator: Ator = Depends(get_ator), s: Servicos = Depends(get_servicos)):
    return s.paineis.admin(ator)


@router.get("/admin/demandas")
def fila(status: str | None = "pendente", ramo: str | None = None,
         ator: Ator = Depends(get_ator), s: Servicos = Depends(get_servicos)):
    """status=pendente (padrão) | validada | encaminhada; use status= vazio para todas."""
    return s.curadoria.fila(ator, status or None, ramo)


@router.get("/admin/demandas/{demanda_id}")
def detalhe(demanda_id: int, ator: Ator = Depends(get_ator), s: Servicos = Depends(get_servicos)):
    return s.curadoria.detalhe(ator, demanda_id)


@router.post("/admin/demandas/{demanda_id}/validar")
def validar(demanda_id: int, ator: Ator = Depends(get_ator), s: Servicos = Depends(get_servicos)):
    return s.curadoria.validar(ator, demanda_id)


@router.post("/admin/demandas/{demanda_id}/encaminhar")
def encaminhar(demanda_id: int, corpo: EncaminharIn, ator: Ator = Depends(get_ator), s: Servicos = Depends(get_servicos)):
    return s.curadoria.encaminhar(ator, demanda_id, corpo.startup_id)


@router.post("/admin/insights/gerar")
def gerar_insights(ator: Ator = Depends(get_ator), s: Servicos = Depends(get_servicos)):
    return s.radar.gerar_insights(ator)


@router.get("/admin/radar")
def radar(ator: Ator = Depends(get_ator), s: Servicos = Depends(get_servicos)):
    return s.radar.radar(ator)


@router.get("/admin/radar/{grupo_id}/demandas")
def demandas_do_grupo(grupo_id: int, ator: Ator = Depends(get_ator), s: Servicos = Depends(get_servicos)):
    return s.radar.demandas_do_grupo(ator, grupo_id)


@router.get("/admin/feedbacks")
def feedbacks(ator: Ator = Depends(get_ator), s: Servicos = Depends(get_servicos)):
    return s.testes.feedbacks(ator)


# --- Leitura para o servidor MCP (RF-MCP-01..03): somente GET ---------------
@router.get("/mcp/radar", tags=["mcp"])
def mcp_listar_radar(ator: Ator = Depends(get_ator), s: Servicos = Depends(get_servicos)):
    return s.mcp.listar_radar(ator)


@router.get("/mcp/startups", tags=["mcp"])
def mcp_buscar_startups(tag: str | None = None, segmento: str | None = None,
                        ator: Ator = Depends(get_ator), s: Servicos = Depends(get_servicos)):
    return s.mcp.buscar_startups(ator, tag, segmento)
