from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_ator, get_servicos
from app.api.schemas import DemandaIn, TesteIn
from app.container import Servicos
from app.core.security import Ator
from app.domain.roteiro import roteiro_publico

router = APIRouter(prefix="/api", tags=["lojista"])


@router.get("/chat/roteiro")
def roteiro():
    """Perguntas e opções do chat guiado (o front não precisa hardcodar)."""
    return roteiro_publico()


@router.get("/lojistas")
def listar_lojistas(ator: Ator = Depends(get_ator), s: Servicos = Depends(get_servicos)):
    return [{"id": l["id"], "nome": l["nome"], "ramo": l["ramo"]} for l in s.lojistas.listar(ator)]


@router.get("/lojistas/{lojista_id}")
def obter_lojista(lojista_id: int, ator: Ator = Depends(get_ator), s: Servicos = Depends(get_servicos)):
    l = s.lojistas.obter(ator, lojista_id)
    return {**l, "texto_demo": l["texto_livre_demo"]}


@router.post("/demandas", status_code=201)
def registrar_demanda(corpo: DemandaIn, ator: Ator = Depends(get_ator), s: Servicos = Depends(get_servicos)):
    """Fecha o chat: classifica (IA ou botões), calcula matching e registra a demanda."""
    return s.demandas.registrar(ator, corpo.lojista_id, corpo.respostas.model_dump(),
                                corpo.texto_livre, corpo.tags)


@router.get("/demandas/{demanda_id}")
def obter_demanda(demanda_id: int, ator: Ator = Depends(get_ator), s: Servicos = Depends(get_servicos)):
    return s.demandas.obter(ator, demanda_id)


@router.get("/demandas/{demanda_id}/matching")
def matching(demanda_id: int, ator: Ator = Depends(get_ator), s: Servicos = Depends(get_servicos)):
    """Ranking com barras por critério (detalhe da startup)."""
    return s.demandas.matching(ator, demanda_id)


@router.post("/testes", status_code=201)
def solicitar_teste(corpo: TesteIn, ator: Ator = Depends(get_ator), s: Servicos = Depends(get_servicos)):
    return s.testes.solicitar(ator, corpo.demanda_id, corpo.startup_id, corpo.autorizacao)


@router.get("/testes/{teste_id}")
def obter_teste(teste_id: int, ator: Ator = Depends(get_ator), s: Servicos = Depends(get_servicos)):
    return s.testes.obter(ator, teste_id)


@router.post("/testes/{teste_id}/feedback-demo")
def feedback_demo(teste_id: int, ator: Ator = Depends(get_ator), s: Servicos = Depends(get_servicos)):
    """Conclui o teste e devolve o feedback pré-preenchido (ciclo fechado da demo)."""
    return s.testes.concluir_com_feedback_demo(ator, teste_id)


@router.get("/feedbacks")
def feedbacks(lojista_id: int | None = None, startup_id: int | None = None,
              ator: Ator = Depends(get_ator), s: Servicos = Depends(get_servicos)):
    return s.testes.feedbacks(ator, lojista_id, startup_id)
