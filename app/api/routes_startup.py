from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_ator, get_servicos
from app.container import Servicos
from app.core.security import Ator

router = APIRouter(prefix="/api", tags=["startup"])


@router.get("/startups")
def listar_startups(tag: str | None = None, segmento: str | None = None,
                    ator: Ator = Depends(get_ator), s: Servicos = Depends(get_servicos)):
    return s.startups.listar(ator, tag, segmento)


@router.get("/startups/{startup_id}")
def obter_startup(startup_id: int, ator: Ator = Depends(get_ator), s: Servicos = Depends(get_servicos)):
    return s.startups.obter(ator, startup_id)


@router.get("/startups/{startup_id}/dashboard")
def dashboard_startup(startup_id: int, ator: Ator = Depends(get_ator), s: Servicos = Depends(get_servicos)):
    return s.paineis.startup(ator, startup_id)


@router.get("/startups/{startup_id}/oportunidades")
def oportunidades(startup_id: int, ator: Ator = Depends(get_ator), s: Servicos = Depends(get_servicos)):
    return s.relatorios.listar_da_startup(ator, startup_id)


@router.get("/relatorios/{relatorio_id}")
def ver_relatorio(relatorio_id: int, versao: str = "anonimizada",
                  ator: Ator = Depends(get_ator), s: Servicos = Depends(get_servicos)):
    """versao=anonimizada | completa (a completa só abre com consentimento do lojista)."""
    return s.relatorios.ver(ator, relatorio_id, versao)
