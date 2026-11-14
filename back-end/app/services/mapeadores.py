"""Conversão linhas do banco -> objetos do domínio de matching."""
from __future__ import annotations

from app.domain.matching import PerfilDemanda, PerfilStartup


def perfil_startup(row: dict) -> PerfilStartup:
    return PerfilStartup(
        id=row["id"], nome=row["nome"], categoria=row["categoria"] or "",
        objetivos=frozenset(row["objetivos"] or []), dores=frozenset(row["dores"] or []),
        tags=frozenset(row["tags"] or []), segmentos=frozenset(row["segmentos"] or []),
        canais=frozenset(row["canais"] or []), preco_min=row["preco_min"], preco_max=row["preco_max"],
        dias_implantacao=row["dias_implantacao"])


def perfil_demanda(lojista: dict, respostas: dict, tags: list[str]) -> PerfilDemanda:
    return PerfilDemanda(
        objetivo=respostas["objetivo"], dificuldade=respostas["dificuldade"],
        canais=frozenset(respostas["canais"]), ferramentas=frozenset(respostas["ferramentas"]),
        orcamento=respostas["orcamento"], urgencia=respostas["urgencia"],
        ramo=lojista["ramo"], tags=frozenset(tags))


def ranking_publico(linhas: list[dict]) -> list[dict]:
    return [{"startup_id": m["startup_id"], "nome": m["nome"], "indice": m["indice"], "motivo": m["motivo"]} for m in linhas]
