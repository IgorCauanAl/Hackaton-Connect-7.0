"""Rotas HTTP do orquestrador (Módulo 03)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from orquestrador.api.deps import get_ator, get_container
from orquestrador.api.schemas import (
    DemandaRequest,
    EncaminharRequest,
    TesteRequest,
)
from orquestrador.container import Container
from orquestrador.domain import Ator
from orquestrador.idempotency import executar_idempotente

router = APIRouter(prefix="/orquestracao", tags=["orquestracao"])


# --------------------------------------------------------------------- RF-01
@router.post("/demandas", status_code=201)
async def registrar_demanda(
    corpo: DemandaRequest,
    request: Request,
    ator: Ator = Depends(get_ator),
    container: Container = Depends(get_container),
):
    """Classifica via IA, registra a demanda e devolve o ranking do matching."""

    async def acao():
        return await container.demandas.registrar(ator, corpo), 201

    return await executar_idempotente(request, corpo, acao)


# --------------------------------------------------------------------- RF-02
@router.get("/demandas/{demanda_id}/matching")
async def obter_matching(
    demanda_id: int,
    ator: Ator = Depends(get_ator),
    container: Container = Depends(get_container),
):
    return await container.demandas.matching(ator, demanda_id)


@router.post("/demandas/{demanda_id}/validar")
async def validar_demanda(
    demanda_id: int,
    request: Request,
    ator: Ator = Depends(get_ator),
    container: Container = Depends(get_container),
):
    """Valida a demanda na curadoria; a autorização real é do backend."""

    async def acao():
        return await container.demandas.validar(ator, demanda_id), 200

    return await executar_idempotente(request, {}, acao)


# --------------------------------------------------------------------- RF-03
@router.post("/insights")
async def gerar_insights(
    request: Request,
    ator: Ator = Depends(get_ator),
    container: Container = Depends(get_container),
):
    """Gera insights via IA (com fallback no backend) e devolve o Radar."""

    async def acao():
        return await container.insights.gerar(ator), 200

    return await executar_idempotente(request, {}, acao)


@router.get("/radar")
async def consultar_radar(
    ator: Ator = Depends(get_ator),
    container: Container = Depends(get_container),
):
    return await container.insights.radar(ator)


@router.get("/padroes")
async def consultar_padroes(
    ator: Ator = Depends(get_ator),
    container: Container = Depends(get_container),
):
    """Radar enriquecido com a tag do grupo (leitura real do backend)."""

    return await container.insights.padroes(ator)


# --------------------------------------------------------------- MCP (leitura)
@router.get("/mcp/radar")
async def mcp_radar(
    ator: Ator = Depends(get_ator),
    container: Container = Depends(get_container),
):
    return await container.mcp.radar(ator)


@router.get("/mcp/startups")
async def mcp_startups(
    tag: str | None = None,
    ator: Ator = Depends(get_ator),
    container: Container = Depends(get_container),
):
    return await container.mcp.startups(ator, tag)


# --------------------------------------------------------------------- RF-04
@router.post("/testes", status_code=201)
async def solicitar_teste(
    corpo: TesteRequest,
    request: Request,
    ator: Ator = Depends(get_ator),
    container: Container = Depends(get_container),
):
    async def acao():
        return await container.testes.solicitar(ator, corpo), 201

    return await executar_idempotente(request, corpo, acao)


@router.get("/testes/{teste_id}")
async def obter_teste(
    teste_id: int,
    ator: Ator = Depends(get_ator),
    container: Container = Depends(get_container),
):
    return await container.testes.obter(ator, teste_id)


@router.post("/testes/{teste_id}/feedback")
async def feedback_demo(
    teste_id: int,
    request: Request,
    ator: Ator = Depends(get_ator),
    container: Container = Depends(get_container),
):
    async def acao():
        return await container.testes.feedback(ator, teste_id), 200

    return await executar_idempotente(request, {}, acao)


# --------------------------------------------------------------------- RF-05
@router.post("/demandas/{demanda_id}/encaminhar")
async def encaminhar_oportunidade(
    demanda_id: int,
    corpo: EncaminharRequest,
    request: Request,
    ator: Ator = Depends(get_ator),
    container: Container = Depends(get_container),
):
    async def acao():
        return (
            await container.relatorios.encaminhar(ator, demanda_id, corpo),
            200,
        )

    return await executar_idempotente(request, corpo, acao)


@router.get("/startups/{startup_id}/relatorios")
async def listar_relatorios(
    startup_id: int,
    ator: Ator = Depends(get_ator),
    container: Container = Depends(get_container),
):
    return await container.relatorios.listar_da_startup(ator, startup_id)


@router.get("/relatorios/{relatorio_id}")
async def ver_relatorio(
    relatorio_id: int,
    versao: str = "anonimizada",
    ator: Ator = Depends(get_ator),
    container: Container = Depends(get_container),
):
    return await container.relatorios.ver(ator, relatorio_id, versao)


__all__ = ["router"]
