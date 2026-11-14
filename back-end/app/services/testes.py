"""Solicitação de teste de 15 dias e feedback (RF-CLI-09/10, BO-RF-06/07)."""
from __future__ import annotations

from datetime import date, timedelta

from app.core.errors import AcessoNegado, RegraDeNegocio
from app.core.security import Ator, Perfil
from app.infra.repositories import (DemandaRepository, FeedbackRepository, MatchRepository, StartupRepository,
                                    TesteRepository, agora)

FEEDBACK_DEMO = {
    "nota": 5, "comentario": "A ferramenta resolveu meu problema de horário. Recomendo!",
    "respostas": {"resolveu_dor": "sim", "facilidade_de_uso": 5, "continuaria_usando": "sim"}}


class TesteService:
    def __init__(self, testes: TesteRepository, demandas: DemandaRepository, matches: MatchRepository,
                 startups: StartupRepository, feedbacks: FeedbackRepository, dias_teste: int = 15):
        self._testes, self._demandas, self._matches = testes, demandas, matches
        self._startups, self._feedbacks, self._dias = startups, feedbacks, dias_teste

    def solicitar(self, ator: Ator, demanda_id: int, startup_id: int, autorizacao: bool) -> dict:
        ator.exige(Perfil.LOJISTA)
        demanda = self._demandas.obter_ou_falhar(demanda_id)
        ator.exige_dono(Perfil.LOJISTA, demanda["lojista_id"])
        if not autorizacao:
            raise RegraDeNegocio("É necessária a autorização expressa para solicitar o teste.")
        if self._matches.obter(demanda_id, startup_id) is None:
            raise RegraDeNegocio("A startup precisa estar entre as recomendadas para esta demanda.")
        startup = self._startups.obter_ou_falhar(startup_id)
        hoje = date.today()
        teste_id = self._testes.criar({
            "demanda_id": demanda_id, "lojista_id": ator.id, "startup_id": startup_id, "autorizacao": 1,
            "consentimento_em": agora(), "status": "solicitado", "inicio": hoje.isoformat(),
            "fim_previsto": (hoje + timedelta(days=self._dias)).isoformat(), "dias": self._dias})
        return {"status": "sucesso", "teste_id": teste_id, "teste_status": "solicitado", "dias": self._dias,
                "mensagem": f"Relatório enviado à {startup['nome']}. Teste de {self._dias} dias iniciado."}

    def obter(self, ator: Ator, teste_id: int) -> dict:
        teste = self._testes.obter_ou_falhar(teste_id)
        self._autorizar_leitura(ator, teste)
        return teste

    def concluir_com_feedback_demo(self, ator: Ator, teste_id: int) -> dict:
        """Simula teste concluído com feedback pré-preenchido (demonstrativo)."""
        ator.exige(Perfil.LOJISTA, Perfil.ADMIN)
        teste = self._testes.obter_ou_falhar(teste_id)
        ator.exige_dono(Perfil.LOJISTA, teste["lojista_id"])
        existente = self._feedbacks.do_teste(teste_id)
        if existente is None:
            self._feedbacks.criar({"teste_id": teste_id, "nota": FEEDBACK_DEMO["nota"],
                                   "comentario": FEEDBACK_DEMO["comentario"], "respostas": FEEDBACK_DEMO["respostas"],
                                   "demonstrativo": 1})
            self._testes.atualizar_status(teste_id, "concluido")
        return self._feedbacks.do_teste(teste_id)

    def feedbacks(self, ator: Ator, lojista_id: int | None = None, startup_id: int | None = None) -> list[dict]:
        if ator.perfil is Perfil.LOJISTA:
            return self._feedbacks.do_lojista(ator.id)
        if ator.perfil is Perfil.STARTUP:  # nunca vê avaliações de outras startups
            return self._feedbacks.da_startup(ator.id)
        ator.exige(Perfil.ADMIN)
        if lojista_id:
            return self._feedbacks.do_lojista(lojista_id)
        if startup_id:
            return self._feedbacks.da_startup(startup_id)
        return self._feedbacks.todos()

    @staticmethod
    def _autorizar_leitura(ator: Ator, teste: dict) -> None:
        if ator.perfil is Perfil.ADMIN:
            return
        dono = (ator.perfil is Perfil.LOJISTA and ator.id == teste["lojista_id"]) or \
               (ator.perfil is Perfil.STARTUP and ator.id == teste["startup_id"])
        if not dono:
            raise AcessoNegado("Você não tem acesso a este teste.")
