"""Dashboards da associação e da startup (RF-ASS-02, RF-STA-02)."""
from __future__ import annotations

from app.core.security import Ator, Perfil
from app.infra.repositories import (DemandaRepository, InsightRepository, LojistaRepository, RelatorioRepository,
                                    StartupRepository, TesteRepository)


class PainelService:
    def __init__(self, lojistas: LojistaRepository, startups: StartupRepository, demandas: DemandaRepository,
                 insights: InsightRepository, relatorios: RelatorioRepository, testes: TesteRepository):
        self._lojistas, self._startups, self._demandas = lojistas, startups, demandas
        self._insights, self._relatorios, self._testes = insights, relatorios, testes

    def admin(self, ator: Ator) -> dict:
        ator.exige(Perfil.ADMIN)
        por_status = self._demandas.contar_por_status()
        return {"lojistas": self._lojistas.contar(), "startups": self._startups.contar(),
                "demandas": self._demandas.contar(), "demandas_pendentes": por_status.get("pendente", 0),
                "demandas_por_status": por_status, "oportunidades_identificadas": len(self._insights.ativos()),
                "demandas_sem_match": len(self._demandas.filtrar(sem_match=True))}

    def startup(self, ator: Ator, startup_id: int) -> dict:
        ator.exige_dono(Perfil.STARTUP, startup_id)
        relatorios = self._relatorios.da_startup(startup_id)
        testes = self._testes.da_startup(startup_id)
        por_status: dict[str, int] = {}
        for t in testes:
            por_status[t["status"]] = por_status.get(t["status"], 0) + 1
        return {"oportunidades_recebidas": len(relatorios), "solicitacoes_de_teste": len(testes),
                "testes_por_status": por_status,
                "recentes": [{"relatorio_id": r["id"], "demanda_id": r["demanda_id"], "criado_em": r["created_at"]}
                             for r in relatorios[:3]]}
