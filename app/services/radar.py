"""Insights e Radar de Oportunidades (BO-RF-09/10, RF-ASS-06/07).

Quantidades e pontuação são calculadas pelo código; a IA só produz a interpretação.
Se a IA falhar, usa-se a versão de referência pré-gerada (origem = 'referencia').
"""
from __future__ import annotations

from app.core.errors import IAIndisponivel
from app.core.security import Ator, Perfil
from app.infra.ia_gateway import IAGateway
from app.infra.repositories import DemandaRepository, InsightRepository

AVISO_IA = "Interpretações sugeridas pela IA; valide antes de tomar decisões."
AVISO_REFERENCIA = "IA indisponível: exibindo sugestões de referência para validação humana."
SUGESTAO_PADRAO = "Dor recorrente entre lojistas: avaliar solução dedicada."


class RadarService:
    def __init__(self, demandas: DemandaRepository, insights: InsightRepository, ia: IAGateway):
        self._demandas, self._insights, self._ia = demandas, insights, ia

    def gerar_insights(self, ator: Ator) -> dict:
        ator.exige(Perfil.ADMIN)
        grupos = self._demandas.agregar_validadas_por_grupo()
        referencia = self._insights.referencia_por_grupo()
        try:
            interpretacoes = self._ia.interpretar_grupos(
                [{"chave": g["tag"], "titulo": g["titulo"], "quantidade": g["quantidade"], "exemplos": g["exemplos"]}
                 for g in grupos])
        except IAIndisponivel:
            interpretacoes = {}
        maior = max((g["quantidade"] for g in grupos), default=1)
        self._insights.desativar_todos()
        for g in grupos:
            interpretacao = str(interpretacoes.get(g["tag"]) or "").strip()
            sugestao = interpretacao or (referencia.get(g["grupo_id"]) or {}).get("sugestao_ia") or SUGESTAO_PADRAO
            self._insights.criar({"grupo_id": g["grupo_id"], "titulo": g["titulo"], "quantidade": g["quantidade"],
                                  "pontuacao": round(100 * g["quantidade"] / maior), "sugestao_ia": sugestao,
                                  "origem": "ia" if interpretacao else "referencia", "ativo": 1})
        return self.radar(ator)

    def radar(self, ator: Ator) -> dict:
        ator.exige(Perfil.ADMIN, Perfil.MCP)
        itens = self._insights.ativos()
        origens = {item["origem"] for item in itens}
        if origens == {"ia"}:
            aviso = AVISO_IA
        elif "ia" not in origens:
            aviso = AVISO_REFERENCIA
        else:
            aviso = "Há análises da IA e sugestões de referência; valide todas antes de tomar decisões."
        return {"aviso": aviso, "radar": [
            {"grupo_id": i["grupo_id"], "tag": i["tag"], "titulo": i["titulo"],
             "quantidade": i["quantidade"], "pontuacao": i["pontuacao"],
             "sugestao": i["sugestao_ia"], "origem": i["origem"], "destaque": n == 0, "requer_validacao_humana": True}
            for n, i in enumerate(itens)]}

    def demandas_do_grupo(self, ator: Ator, grupo_id: int) -> list[dict]:
        ator.exige(Perfil.ADMIN)
        return [{"id": d["id"], "titulo": d["titulo"], "ramo": d["ramo"], "status": d["status"]}
                for d in self._demandas.do_grupo(grupo_id)]
