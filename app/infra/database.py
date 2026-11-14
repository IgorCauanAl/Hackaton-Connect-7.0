"""SQLite: conexão e schema. Colunas *_json guardam listas/objetos serializados."""
from __future__ import annotations

import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS lojistas (
  id INTEGER PRIMARY KEY, nome TEXT NOT NULL, ramo TEXT NOT NULL, tipo TEXT, porte TEXT,
  cidade TEXT, regiao TEXT, canais_json TEXT NOT NULL, ferramentas_json TEXT NOT NULL,
  texto_livre_demo TEXT, respostas_demo_json TEXT
);
CREATE TABLE IF NOT EXISTS startups (
  id INTEGER PRIMARY KEY, nome TEXT NOT NULL, descricao TEXT, solucao TEXT, portfolio_url TEXT,
  whatsapp TEXT, categoria TEXT, objetivos_json TEXT, dores_json TEXT, tags_json TEXT,
  segmentos_json TEXT, canais_json TEXT, preco_min REAL, preco_max REAL, dias_implantacao INTEGER
);
CREATE TABLE IF NOT EXISTS grupos (
  id INTEGER PRIMARY KEY, tag TEXT NOT NULL UNIQUE, titulo TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS demandas (
  id INTEGER PRIMARY KEY AUTOINCREMENT, lojista_id INTEGER REFERENCES lojistas(id),
  ramo TEXT, regiao TEXT, titulo TEXT, texto TEXT NOT NULL, respostas_json TEXT, tags_json TEXT NOT NULL,
  tags_origem TEXT, status TEXT NOT NULL DEFAULT 'pendente', origem TEXT NOT NULL,
  sem_match INTEGER NOT NULL DEFAULT 0, grupo_id INTEGER REFERENCES grupos(id),
  validada_por TEXT, validada_em TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS historico_demanda (
  id INTEGER PRIMARY KEY AUTOINCREMENT, demanda_id INTEGER NOT NULL REFERENCES demandas(id),
  evento TEXT NOT NULL, detalhe TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS matches (
  id INTEGER PRIMARY KEY AUTOINCREMENT, demanda_id INTEGER NOT NULL REFERENCES demandas(id),
  startup_id INTEGER NOT NULL REFERENCES startups(id), indice INTEGER NOT NULL,
  motivo TEXT, criterios_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS testes (
  id INTEGER PRIMARY KEY AUTOINCREMENT, demanda_id INTEGER NOT NULL REFERENCES demandas(id),
  lojista_id INTEGER NOT NULL REFERENCES lojistas(id), startup_id INTEGER NOT NULL REFERENCES startups(id),
  autorizacao INTEGER NOT NULL, consentimento_em TEXT NOT NULL, status TEXT NOT NULL,
  inicio TEXT NOT NULL, fim_previsto TEXT NOT NULL, dias INTEGER NOT NULL, created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS feedbacks (
  id INTEGER PRIMARY KEY AUTOINCREMENT, teste_id INTEGER NOT NULL UNIQUE REFERENCES testes(id),
  nota INTEGER NOT NULL, comentario TEXT, respostas_json TEXT, demonstrativo INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS insights (
  id INTEGER PRIMARY KEY AUTOINCREMENT, grupo_id INTEGER NOT NULL REFERENCES grupos(id),
  titulo TEXT NOT NULL, quantidade INTEGER NOT NULL, pontuacao INTEGER NOT NULL DEFAULT 0,
  sugestao_ia TEXT, origem TEXT NOT NULL, ativo INTEGER NOT NULL DEFAULT 1, gerado_em TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS relatorios (
  id INTEGER PRIMARY KEY AUTOINCREMENT, demanda_id INTEGER NOT NULL REFERENCES demandas(id),
  startup_id INTEGER NOT NULL REFERENCES startups(id), blocos_json TEXT NOT NULL, created_at TEXT NOT NULL,
  UNIQUE (demanda_id, startup_id)
);
"""


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def drop_all(conn: sqlite3.Connection) -> None:
    tabelas = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    conn.execute("PRAGMA foreign_keys = OFF")
    for t in tabelas:
        conn.execute(f"DROP TABLE IF EXISTS {t}")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
