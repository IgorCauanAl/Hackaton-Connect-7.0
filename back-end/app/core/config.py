"""Configuração central, lida do ambiente (12-factor)."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


@dataclass(frozen=True)
class Settings:
    db_path: str = "facesp_demo.db"
    ia_url: str = ""
    ia_timeout: float = 2.0
    dias_teste: int = 15

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            db_path=os.getenv("FACESP_DB_PATH", cls.db_path),
            ia_url=os.getenv("FACESP_IA_URL", ""),
            ia_timeout=float(os.getenv("FACESP_IA_TIMEOUT", "2")),
        )


def carregar_json(nome: str) -> dict:
    return json.loads((CONFIG_DIR / nome).read_text(encoding="utf-8"))
