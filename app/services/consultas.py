"""Consultas de lojistas e startups (BO-RF-02, BO-RF-04) e leitura MCP (RF-MCP-01..03)."""
from __future__ import annotations

from app.core.security import Ator, Perfil
from app.infra.repositories import InsightRepository, LojistaRepository, StartupRepository


class LojistaService:
    def __init__(self, lojistas: LojistaRepository):
        self._lojistas = lojistas

    def listar(self, ator: Ator) -> list[dict]:
        ator.exige(Perfil.ADMIN, Perfil.LOJISTA)
        itens = self._lojistas.listar()
        return itens if ator.perfil is Perfil.ADMIN else [i for i in itens if i["id"] == ator.id]

    def obter(self, ator: Ator, lojista_id: int) -> dict:
        ator.exige_dono(Perfil.LOJISTA, lojista_id)
        return self._lojistas.obter_ou_falhar(lojista_id)


class StartupService:
    def __init__(self, startups: StartupRepository):
        self._startups = startups

    def listar(self, ator: Ator, tag: str | None = None, segmento: str | None = None) -> list[dict]:
        ator.exige(Perfil.ADMIN, Perfil.MCP, Perfil.STARTUP, Perfil.LOJISTA)
        itens = self._startups.listar()
        if tag:
            itens = [s for s in itens if tag in (s["tags"] or [])]
        if segmento:
            itens = [s for s in itens if segmento in (s["segmentos"] or [])]
        return itens

    def obter(self, ator: Ator, startup_id: int) -> dict:
        ator.exige(Perfil.ADMIN, Perfil.MCP, Perfil.STARTUP, Perfil.LOJISTA)
        return self._startups.obter_ou_falhar(startup_id)


class LeituraMcpService:
    """Fachada somente leitura: a base das duas ferramentas MCP (listar_radar, buscar_startups).

    O servidor FastMCP do colega pode importar esta classe ou chamar /api/mcp/*.
    Não há nenhum método de escrita (RF-MCP-03).
    """

    def __init__(self, insights: InsightRepository, startups: StartupService):
        self._insights = insights
        self._startups = startups

    def listar_radar(self, ator: Ator) -> list[dict]:
        ator.exige(Perfil.ADMIN, Perfil.MCP)
        return [{"dor": i["titulo"], "tag": i["tag"], "quantidade": i["quantidade"],
                 "sugestao_ia": i["sugestao_ia"], "origem": i["origem"]}
                for i in self._insights.ativos()]

    def buscar_startups(self, ator: Ator, tag: str | None = None, segmento: str | None = None) -> list[dict]:
        itens = self._startups.listar(ator, tag, segmento)
        return [{"id": s["id"], "nome": s["nome"], "descricao": s["descricao"], "solucao": s["solucao"],
                 "segmentos": s["segmentos"], "tags": s["tags"]} for s in itens]
