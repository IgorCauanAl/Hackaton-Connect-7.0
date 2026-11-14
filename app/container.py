"""Composition root: monta repositórios e serviços para uma conexão (DI manual)."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from app.core.config import Settings, carregar_json
from app.domain.matching import MotorMatching
from app.infra import repositories as r
from app.infra.ia_gateway import HttpIAGateway, IAGateway, IAIndisponivelGateway
from app.services.consultas import LeituraMcpService, LojistaService, StartupService
from app.services.curadoria import CuradoriaService
from app.services.demandas import DemandaService
from app.services.paineis import PainelService
from app.services.radar import RadarService
from app.services.relatorios import RelatorioService
from app.services.testes import TesteService


def criar_ia(settings: Settings) -> IAGateway:
    if settings.ia_url:
        return HttpIAGateway(settings.ia_url, settings.ia_timeout)
    return IAIndisponivelGateway()


@dataclass
class Servicos:
    lojistas: LojistaService
    startups: StartupService
    demandas: DemandaService
    testes: TesteService
    curadoria: CuradoriaService
    radar: RadarService
    relatorios: RelatorioService
    paineis: PainelService
    mcp: LeituraMcpService


def montar(conn: sqlite3.Connection, settings: Settings, ia: IAGateway | None = None) -> Servicos:
    ia = ia or criar_ia(settings)
    motor = MotorMatching.de_config(carregar_json("matching.json"))
    lojistas, startups = r.LojistaRepository(conn), r.StartupRepository(conn)
    demandas, grupos = r.DemandaRepository(conn), r.GrupoRepository(conn)
    matches, historico = r.MatchRepository(conn), r.HistoricoRepository(conn)
    testes, feedbacks = r.TesteRepository(conn), r.FeedbackRepository(conn)
    insights, relatorios_repo = r.InsightRepository(conn), r.RelatorioRepository(conn)

    relatorios = RelatorioService(relatorios_repo, demandas, lojistas, startups, matches, testes)
    startup_service = StartupService(startups)
    return Servicos(
        lojistas=LojistaService(lojistas), startups=startup_service,
        demandas=DemandaService(demandas, lojistas, startups, grupos, matches, historico, motor, ia),
        testes=TesteService(testes, demandas, matches, startups, feedbacks, settings.dias_teste),
        curadoria=CuradoriaService(demandas, historico, matches, startups, relatorios),
        radar=RadarService(demandas, insights, ia), relatorios=relatorios,
        paineis=PainelService(lojistas, startups, demandas, insights, relatorios_repo, testes),
        mcp=LeituraMcpService(insights, startup_service))
