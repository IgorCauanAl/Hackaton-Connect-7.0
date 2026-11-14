"""Rotas HTTP do serviço de IA."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request

from ia_mcp.api.schemas import (
    ClassificarRequest,
    ClassificarResponse,
    InsightsRequest,
    InsightsResponse,
    ResumirRequest,
    ResumirResponse,
)
from ia_mcp.services.facade import IAMCPService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ia", tags=["ia"])


def _service(request: Request) -> IAMCPService:
    service = getattr(request.app.state, "ia", None)
    if service is None:  # pragma: no cover - proteção de configuração
        raise RuntimeError("Serviço IA/MCP não inicializado na aplicação")
    return service


def _log_text(request: Request, endpoint: str, text: str) -> None:
    settings = getattr(request.app.state, "settings", None)
    if settings is not None and settings.log_text:
        logger.debug("%s texto=%r", endpoint, text)


@router.post("/classificar", response_model=ClassificarResponse)
async def classificar(
    payload: ClassificarRequest, request: Request
) -> ClassificarResponse:
    _log_text(request, "classificar", payload.texto)
    tags = await _service(request).classificar(payload.texto)
    return ClassificarResponse(tags=tags)


@router.post("/resumir", response_model=ResumirResponse)
async def resumir(payload: ResumirRequest, request: Request) -> ResumirResponse:
    _log_text(request, "resumir", payload.texto)
    resumo = await _service(request).resumir(payload.texto)
    return ResumirResponse(resumo=resumo)


@router.post("/insights", response_model=InsightsResponse)
async def insights(
    payload: InsightsRequest, request: Request
) -> InsightsResponse:
    interpretacoes = await _service(request).interpretar(payload.grupos)
    return InsightsResponse(interpretacoes=interpretacoes)


__all__ = ["router"]
