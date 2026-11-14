"""Repositórios (Repository pattern): únicas classes que conhecem SQL.

Retornam dicts com colunas *_json já decodificadas (sem o sufixo).
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Iterable

from app.core.errors import NaoEncontrado


def agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _linha(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    out = {}
    for chave in row.keys():
        valor = row[chave]
        if chave.endswith("_json"):
            out[chave[:-5]] = json.loads(valor) if valor else None
        else:
            out[chave] = valor
    return out


class BaseRepository:
    tabela = ""
    rotulo = "Registro"

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def _um(self, sql: str, params: Iterable[Any] = ()) -> dict | None:
        return _linha(self.conn.execute(sql, tuple(params)).fetchone())

    def _todos(self, sql: str, params: Iterable[Any] = ()) -> list[dict]:
        return [_linha(r) for r in self.conn.execute(sql, tuple(params)).fetchall()]

    def _insert(self, tabela: str, dados: dict) -> int:
        colunas = {r["name"] for r in self.conn.execute(f"PRAGMA table_info({tabela})")}
        linha = {}
        for chave, valor in dados.items():
            if f"{chave}_json" in colunas:  # coluna JSON: serializa (None vira NULL)
                linha[f"{chave}_json"] = None if valor is None else json.dumps(valor, ensure_ascii=False)
            else:
                linha[chave] = valor
        cols = ", ".join(linha)
        marks = ", ".join("?" for _ in linha)
        cur = self.conn.execute(f"INSERT INTO {tabela} ({cols}) VALUES ({marks})", tuple(linha.values()))
        return cur.lastrowid

    def obter(self, id_: int) -> dict | None:
        return self._um(f"SELECT * FROM {self.tabela} WHERE id = ?", (id_,))

    def obter_ou_falhar(self, id_: int) -> dict:
        achado = self.obter(id_)
        if achado is None:
            raise NaoEncontrado(f"{self.rotulo} {id_} não encontrado(a).")
        return achado

    def listar(self) -> list[dict]:
        return self._todos(f"SELECT * FROM {self.tabela} ORDER BY id")

    def contar(self) -> int:
        return self.conn.execute(f"SELECT COUNT(*) FROM {self.tabela}").fetchone()[0]


class LojistaRepository(BaseRepository):
    tabela, rotulo = "lojistas", "Lojista"

    def criar(self, dados: dict) -> int:  # usado só pelo seed
        return self._insert("lojistas", dados)


class StartupRepository(BaseRepository):
    tabela, rotulo = "startups", "Startup"

    def criar(self, dados: dict) -> int:  # usado só pelo seed
        return self._insert("startups", dados)


class GrupoRepository(BaseRepository):
    tabela, rotulo = "grupos", "Grupo"

    def criar(self, dados: dict) -> int:
        return self._insert("grupos", dados)

    def por_tags(self, tags: Iterable[str]) -> dict | None:
        for tag in tags:  # a ordem das tags define a prioridade
            achado = self._um("SELECT * FROM grupos WHERE tag = ?", (tag,))
            if achado:
                return achado
        return None


class DemandaRepository(BaseRepository):
    tabela, rotulo = "demandas", "Demanda"

    def criar(self, dados: dict) -> int:
        ts = agora()
        return self._insert("demandas", {**dados, "created_at": ts, "updated_at": ts})

    def filtrar(self, status: str | None = None, ramo: str | None = None, sem_match: bool | None = None) -> list[dict]:
        sql, params = "SELECT * FROM demandas WHERE 1=1", []
        if status:
            sql += " AND status = ?"; params.append(status)
        if ramo:
            sql += " AND ramo = ?"; params.append(ramo)
        if sem_match is not None:
            sql += " AND sem_match = ?"; params.append(int(sem_match))
        return self._todos(sql + " ORDER BY id", params)

    def atualizar_status(self, id_: int, status: str, validada_por: str | None = None) -> None:
        ts = agora()
        if validada_por:
            self.conn.execute("UPDATE demandas SET status=?, validada_por=?, validada_em=?, updated_at=? WHERE id=?",
                              (status, validada_por, ts, ts, id_))
        else:
            self.conn.execute("UPDATE demandas SET status=?, updated_at=? WHERE id=?", (status, ts, id_))

    def contar_por_status(self) -> dict[str, int]:
        rows = self.conn.execute("SELECT status, COUNT(*) c FROM demandas GROUP BY status").fetchall()
        return {r["status"]: r["c"] for r in rows}

    def agregar_validadas_por_grupo(self) -> list[dict]:
        """Só demandas validadas/encaminhadas entram em insights (BO-RF-08)."""
        grupos = self._todos(
            "SELECT g.id grupo_id, g.tag, g.titulo, COUNT(d.id) quantidade FROM grupos g "
            "JOIN demandas d ON d.grupo_id = g.id AND d.status IN ('validada','encaminhada') "
            "GROUP BY g.id ORDER BY quantidade DESC, g.titulo")
        for g in grupos:
            linhas = self.conn.execute(
                "SELECT texto, regiao FROM demandas WHERE grupo_id=? AND status IN ('validada','encaminhada') ORDER BY id",
                (g["grupo_id"],)).fetchall()
            g["exemplos"] = [r["texto"] for r in linhas[:5]]
            g["regioes"] = sorted({r["regiao"] for r in linhas if r["regiao"]})
        return grupos

    def do_grupo(self, grupo_id: int) -> list[dict]:
        return self._todos("SELECT * FROM demandas WHERE grupo_id = ? ORDER BY id", (grupo_id,))

    def contar_sinal(self, tag: str, ramo: str | None, regiao: str | None, excluir_id: int) -> dict:
        """Sinal de mercado: quantas demandas validadas relatam a mesma dor."""
        validas = self._todos("SELECT ramo, regiao, tags_json FROM demandas WHERE status IN ('validada','encaminhada') AND id != ?",
                              (excluir_id,))
        mesma = [d for d in validas if tag in d["tags"]]
        return {"total": len(mesma),
                "mesmo_ramo": sum(1 for d in mesma if ramo and d["ramo"] == ramo),
                "mesma_regiao": sum(1 for d in mesma if regiao and d["regiao"] == regiao)}


class HistoricoRepository(BaseRepository):
    tabela = "historico_demanda"

    def registrar(self, demanda_id: int, evento: str, detalhe: str = "") -> None:
        self._insert("historico_demanda", {"demanda_id": demanda_id, "evento": evento, "detalhe": detalhe, "created_at": agora()})

    def da_demanda(self, demanda_id: int) -> list[dict]:
        return self._todos("SELECT evento, detalhe, created_at FROM historico_demanda WHERE demanda_id=? ORDER BY id", (demanda_id,))


class MatchRepository(BaseRepository):
    tabela = "matches"

    def salvar(self, demanda_id: int, recomendacoes) -> None:
        self.conn.execute("DELETE FROM matches WHERE demanda_id = ?", (demanda_id,))
        for r in recomendacoes:
            self._insert("matches", {"demanda_id": demanda_id, "startup_id": r.startup_id, "indice": r.indice,
                                     "motivo": r.motivo, "criterios": [c.to_dict() for c in r.criterios]})

    def da_demanda(self, demanda_id: int) -> list[dict]:
        return self._todos(
            "SELECT m.*, s.nome FROM matches m JOIN startups s ON s.id = m.startup_id "
            "WHERE m.demanda_id = ? ORDER BY m.indice DESC, s.nome", (demanda_id,))

    def obter(self, demanda_id: int, startup_id: int) -> dict | None:  # type: ignore[override]
        return self._um("SELECT * FROM matches WHERE demanda_id=? AND startup_id=?", (demanda_id, startup_id))


class TesteRepository(BaseRepository):
    tabela, rotulo = "testes", "Teste"

    def criar(self, dados: dict) -> int:
        ts = agora()
        return self._insert("testes", {**dados, "created_at": ts, "updated_at": ts})

    def atualizar_status(self, id_: int, status: str) -> None:
        self.conn.execute("UPDATE testes SET status=?, updated_at=? WHERE id=?", (status, agora(), id_))

    def da_startup(self, startup_id: int) -> list[dict]:
        return self._todos("SELECT * FROM testes WHERE startup_id=? ORDER BY id DESC", (startup_id,))

    def autorizado(self, demanda_id: int, startup_id: int) -> bool:
        return self._um("SELECT id FROM testes WHERE demanda_id=? AND startup_id=? AND autorizacao=1",
                        (demanda_id, startup_id)) is not None


class FeedbackRepository(BaseRepository):
    tabela, rotulo = "feedbacks", "Feedback"

    _BASE = ("SELECT f.*, t.lojista_id, t.startup_id, t.demanda_id, t.status teste_status, s.nome startup_nome "
             "FROM feedbacks f JOIN testes t ON t.id=f.teste_id JOIN startups s ON s.id=t.startup_id ")

    def criar(self, dados: dict) -> int:
        return self._insert("feedbacks", {**dados, "created_at": agora()})

    def do_teste(self, teste_id: int) -> dict | None:
        return self._um(self._BASE + "WHERE f.teste_id=?", (teste_id,))

    def do_lojista(self, lojista_id: int) -> list[dict]:
        return self._todos(self._BASE + "WHERE t.lojista_id=? ORDER BY f.id DESC", (lojista_id,))

    def da_startup(self, startup_id: int) -> list[dict]:
        return self._todos(self._BASE + "WHERE t.startup_id=? ORDER BY f.id DESC", (startup_id,))

    def todos(self) -> list[dict]:
        return self._todos(self._BASE + "ORDER BY f.id DESC")


class InsightRepository(BaseRepository):
    tabela = "insights"

    def criar(self, dados: dict) -> int:
        return self._insert("insights", {**dados, "gerado_em": agora()})

    def desativar_todos(self) -> None:
        self.conn.execute("UPDATE insights SET ativo = 0")

    def ativos(self) -> list[dict]:
        return self._todos("SELECT * FROM insights WHERE ativo=1 ORDER BY quantidade DESC, titulo")

    def referencia_por_grupo(self) -> dict[int, dict]:
        return {r["grupo_id"]: r for r in self._todos("SELECT * FROM insights WHERE origem='referencia' ORDER BY id")}


class RelatorioRepository(BaseRepository):
    tabela, rotulo = "relatorios", "Relatório"

    def salvar(self, demanda_id: int, startup_id: int, blocos: dict) -> int:
        self.conn.execute("DELETE FROM relatorios WHERE demanda_id=? AND startup_id=?", (demanda_id, startup_id))
        return self._insert("relatorios", {"demanda_id": demanda_id, "startup_id": startup_id, "blocos": blocos, "created_at": agora()})

    def da_startup(self, startup_id: int) -> list[dict]:
        return self._todos("SELECT * FROM relatorios WHERE startup_id=? ORDER BY id DESC", (startup_id,))
