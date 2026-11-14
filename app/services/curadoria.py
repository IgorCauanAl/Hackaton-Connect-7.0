"""Curadoria de demandas pela associação (BO-RF-08, RF-ASS-03..05, RF-ASS-11)."""
from __future__ import annotations

from app.core.errors import RegraDeNegocio
from app.core.security import Ator, Perfil
from app.infra.repositories import DemandaRepository, HistoricoRepository, MatchRepository, StartupRepository
from app.services.demandas import exigir_demanda_validada
from app.services.relatorios import RelatorioService


class CuradoriaService:
    def __init__(self, demandas: DemandaRepository, historico: HistoricoRepository, matches: MatchRepository,
                 startups: StartupRepository, relatorios: RelatorioService):
        self._demandas, self._historico, self._matches = demandas, historico, matches
        self._startups, self._relatorios = startups, relatorios

    def fila(self, ator: Ator, status: str | None = "pendente", ramo: str | None = None) -> list[dict]:
        ator.exige(Perfil.ADMIN)
        return [{"id": d["id"], "texto": d["texto"], "titulo": d["titulo"], "ramo": d["ramo"], "tags": d["tags"],
                 "status": d["status"], "sem_match": bool(d["sem_match"]), "lojista_id": d["lojista_id"]}
                for d in self._demandas.filtrar(status=status, ramo=ramo)]

    def detalhe(self, ator: Ator, demanda_id: int) -> dict:
        ator.exige(Perfil.ADMIN)
        d = self._demandas.obter_ou_falhar(demanda_id)
        return {**d, "matching": self._matches.da_demanda(demanda_id), "historico": self._historico.da_demanda(demanda_id)}

    def validar(self, ator: Ator, demanda_id: int) -> dict:
        ator.exige(Perfil.ADMIN)
        d = self._demandas.obter_ou_falhar(demanda_id)
        if d["status"] != "pendente":
            raise RegraDeNegocio(f"Só demandas pendentes podem ser validadas (status atual: {d['status']}).")
        self._demandas.atualizar_status(demanda_id, "validada", validada_por="admin")
        self._historico.registrar(demanda_id, "validada", "Validada pela associação")
        return {"status": "validado", "demanda_id": demanda_id}

    def encaminhar(self, ator: Ator, demanda_id: int, startup_id: int) -> dict:
        """Encaminha ao 'Connect': gera o relatório para a startup e muda o status."""
        ator.exige(Perfil.ADMIN)
        d = self._demandas.obter_ou_falhar(demanda_id)
        exigir_demanda_validada(d)
        startup = self._startups.obter_ou_falhar(startup_id)
        relatorio_id = self._relatorios.gerar(demanda_id, startup_id)
        self._demandas.atualizar_status(demanda_id, "encaminhada")
        self._historico.registrar(demanda_id, "encaminhada", f"Relatório enviado a {startup['nome']}")
        return {"status": "encaminhada", "demanda_id": demanda_id, "relatorio_id": relatorio_id}
