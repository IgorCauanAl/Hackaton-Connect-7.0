"""Relatório de 6 blocos para a startup, em versão anonimizada e completa (BO-RF-11)."""
from __future__ import annotations

from app.core.errors import AcessoNegado, RegraDeNegocio
from app.core.security import Ator, Perfil
from app.infra.repositories import (DemandaRepository, LojistaRepository, MatchRepository, RelatorioRepository,
                                    StartupRepository, TesteRepository)
from app.services.demandas import exigir_demanda_validada

BLOCOS = ("resumo", "perfil_loja", "dor_contexto", "compatibilidade", "sinal_mercado", "proximo_passo")


class RelatorioService:
    def __init__(self, relatorios: RelatorioRepository, demandas: DemandaRepository, lojistas: LojistaRepository,
                 startups: StartupRepository, matches: MatchRepository, testes: TesteRepository):
        self._relatorios, self._demandas, self._lojistas = relatorios, demandas, lojistas
        self._startups, self._matches, self._testes = startups, matches, testes

    def gerar(self, demanda_id: int, startup_id: int) -> int:
        """Chamado pela curadoria ao encaminhar. Guarda os blocos 1-5; o 6 é montado na leitura."""
        demanda = self._demandas.obter_ou_falhar(demanda_id)
        exigir_demanda_validada(demanda)
        self._startups.obter_ou_falhar(startup_id)
        lojista = self._lojistas.obter(demanda["lojista_id"]) if demanda["lojista_id"] else None
        match = self._matches.obter(demanda_id, startup_id)
        respostas = demanda["respostas"] or {}
        tag = demanda["tags"][0] if demanda["tags"] else None
        sinal = self._demandas.contar_sinal(tag, demanda["ramo"], demanda["regiao"], demanda_id) if tag else \
            {"total": 0, "mesmo_ramo": 0, "mesma_regiao": 0}
        blocos = {
            "resumo": {"resumo": demanda["titulo"], "urgencia": respostas.get("urgencia"),
                       "indice": match["indice"] if match else None},
            "perfil_loja": {"nome": lojista["nome"] if lojista else None, "ramo": demanda["ramo"],
                            "tipo": lojista["tipo"] if lojista else None, "porte": lojista["porte"] if lojista else None,
                            "cidade": lojista["cidade"] if lojista else None, "regiao": demanda["regiao"],
                            "canais": respostas.get("canais"), "ferramentas": respostas.get("ferramentas")},
            "dor_contexto": {"respostas": respostas, "texto_livre": demanda["texto"], "tags": demanda["tags"],
                             "resumo": demanda["titulo"]},
            "compatibilidade": {"indice": match["indice"], "criterios": [
                {"criterio": c["criterio"], "pontuacao": c["pontuacao"], "motivo": c["motivo"]} for c in match["criterios"]]
            } if match else None,
            "sinal_mercado": {"lojistas_mesma_dor": sinal["total"], "no_mesmo_ramo": sinal["mesmo_ramo"],
                              "na_mesma_regiao": sinal["mesma_regiao"]},
        }
        return self._relatorios.salvar(demanda_id, startup_id, blocos)

    def listar_da_startup(self, ator: Ator, startup_id: int) -> list[dict]:
        ator.exige_dono(Perfil.STARTUP, startup_id)
        itens = []
        for r in self._relatorios.da_startup(startup_id):
            d = self._demandas.obter_ou_falhar(r["demanda_id"])
            itens.append({"relatorio_id": r["id"], "demanda_id": d["id"], "titulo": d["titulo"], "ramo": d["ramo"],
                          "tags": d["tags"], "status": d["status"], "criado_em": r["created_at"]})
        return itens

    def ver(self, ator: Ator, relatorio_id: int, versao: str = "anonimizada") -> dict:
        rel = self._relatorios.obter_ou_falhar(relatorio_id)
        ator.exige(Perfil.STARTUP, Perfil.ADMIN)
        ator.exige_dono(Perfil.STARTUP, rel["startup_id"])
        if versao not in ("anonimizada", "completa"):
            raise RegraDeNegocio("Versão inválida: use 'anonimizada' ou 'completa'.")
        blocos = rel["blocos"]
        if versao == "anonimizada":
            perfil = blocos["perfil_loja"]
            dor = blocos["dor_contexto"]
            visivel = {
                "resumo": blocos["resumo"],
                "perfil_loja": {k: perfil.get(k) for k in ("ramo", "tipo", "porte", "regiao")},
                "dor_contexto": {"tags": dor["tags"], "resumo": dor["resumo"]},
                "compatibilidade": blocos["compatibilidade"], "sinal_mercado": blocos["sinal_mercado"]}
        else:
            if not self._testes.autorizado(rel["demanda_id"], rel["startup_id"]):
                raise AcessoNegado("A versão completa só abre com o consentimento do lojista.")
            teste = next(t for t in self._testes.da_startup(rel["startup_id"]) if t["demanda_id"] == rel["demanda_id"])
            visivel = {**blocos, "proximo_passo": {
                "canal": "whatsapp", "data_pedido_teste": teste["created_at"], "consentimento_em": teste["consentimento_em"],
                "janela_dias": teste["dias"], "fim_previsto": teste["fim_previsto"]}}
        return {"relatorio_id": relatorio_id, "demanda_id": rel["demanda_id"], "startup_id": rel["startup_id"],
                "versao": versao, "gerado_em": rel["created_at"], "blocos": visivel}
