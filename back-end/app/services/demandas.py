"""Registro de demandas (chat guiado) + classificação com fallback (RF-CLI-04/05/08)."""
from __future__ import annotations

from app.core.config import carregar_json
from app.core.errors import IAIndisponivel, RegraDeNegocio
from app.core.security import Ator, Perfil
from app.domain.matching import MotorMatching
from app.infra.ia_gateway import IAGateway
from app.infra.repositories import (DemandaRepository, GrupoRepository, HistoricoRepository, LojistaRepository,
                                    MatchRepository, StartupRepository)
from app.services.mapeadores import perfil_demanda, perfil_startup, ranking_publico

MSG_SEM_MATCH = ("Nenhuma solução disponível atende suficientemente à sua necessidade. "
                 "Sua demanda foi encaminhada para análise da associação.")


class DemandaService:
    def __init__(self, demandas: DemandaRepository, lojistas: LojistaRepository, startups: StartupRepository,
                 grupos: GrupoRepository, matches: MatchRepository, historico: HistoricoRepository,
                 motor: MotorMatching, ia: IAGateway):
        self._demandas, self._lojistas, self._startups = demandas, lojistas, startups
        self._grupos, self._matches, self._historico = grupos, matches, historico
        self._motor, self._ia = motor, ia
        vocab = carregar_json("vocabulario.json")
        self._vocabulario = set(vocab["tags"])
        self._tags_por_dificuldade = vocab["tags_por_dificuldade"]

    # ----------------------------------------------------------- caso de uso
    def registrar(self, ator: Ator, lojista_id: int, respostas: dict, texto_livre: str,
                  tags: list[str] | None = None) -> dict:
        ator.exige_dono(Perfil.LOJISTA, lojista_id)
        lojista = self._lojistas.obter_ou_falhar(lojista_id)
        tags, origem_tags = self._classificar(texto_livre, respostas, tags)
        resultado = self._motor.calcular(perfil_demanda(lojista, respostas, tags),
                                         [perfil_startup(s) for s in self._startups.listar()])
        grupo = self._grupos.por_tags(tags)
        titulo = self._resumir(texto_livre)
        demanda_id = self._demandas.criar({
            "lojista_id": lojista_id, "ramo": lojista["ramo"], "regiao": lojista["regiao"], "titulo": titulo,
            "texto": texto_livre, "respostas": respostas, "tags": tags, "tags_origem": origem_tags,
            "status": "pendente", "origem": "chat_guiado", "sem_match": int(resultado.sem_match),
            "grupo_id": grupo["id"] if grupo else None})
        self._historico.registrar(demanda_id, "registrada", "Chat guiado concluído")
        self._historico.registrar(demanda_id, "classificada", f"Tags {tags} (origem: {origem_tags})")
        self._matches.salvar(demanda_id, resultado.recomendacoes)
        if resultado.sem_match:
            self._historico.registrar(demanda_id, "sem_match", "Encaminhada à fila de curadoria")
        else:
            self._historico.registrar(demanda_id, "matching", f"{len(resultado.recomendacoes)} recomendação(ões)")
        return {"demanda_id": demanda_id, "status": "sem_match" if resultado.sem_match else "sucesso",
                "tags_identificadas": tags, "tags_origem": origem_tags,
                "ranking_startups": ranking_publico(self._matches.da_demanda(demanda_id)),
                "mensagem": MSG_SEM_MATCH if resultado.sem_match else None}

    def obter(self, ator: Ator, demanda_id: int) -> dict:
        demanda = self._demandas.obter_ou_falhar(demanda_id)
        if ator.perfil is Perfil.LOJISTA:
            ator.exige_dono(Perfil.LOJISTA, demanda["lojista_id"])
        else:
            ator.exige(Perfil.ADMIN)
        return demanda

    def matching(self, ator: Ator, demanda_id: int) -> dict:
        demanda = self.obter(ator, demanda_id)
        linhas = self._matches.da_demanda(demanda_id)
        return {"demanda_id": demanda_id, "sem_match": bool(demanda["sem_match"]),
                "ranking_startups": [{**ranking_publico([m])[0], "criterios": m["criterios"]} for m in linhas]}

    # --------------------------------------------------------------- helpers
    def _classificar(self, texto: str, respostas: dict,
                     tags: list[str] | None = None) -> tuple[list[str], str]:
        if tags:
            fornecidas = [t for t in tags if t in self._vocabulario]
            if fornecidas:
                return fornecidas, "ia"
        try:
            identificadas = [t for t in self._ia.extrair_tags(texto) if t in self._vocabulario]
            if identificadas:
                return identificadas, "ia"
        except IAIndisponivel:
            pass
        return list(self._tags_por_dificuldade.get(respostas["dificuldade"], [])), "botoes"

    def _resumir(self, texto: str) -> str:
        try:
            return self._ia.resumir(texto)
        except IAIndisponivel:
            return texto if len(texto) <= 80 else texto[:77].rstrip() + "..."


def exigir_demanda_validada(demanda: dict) -> None:
    if demanda["status"] not in ("validada", "encaminhada"):
        raise RegraDeNegocio("A demanda precisa estar validada.")
