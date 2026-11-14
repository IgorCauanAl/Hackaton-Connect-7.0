"""Configuração central do serviço IA/MCP.

Todas as variáveis de ambiente usam o prefixo ``IA_MCP_``. Nenhuma URL,
credencial ou caminho de recurso externo é fixada no código: os padrões
existem apenas para permitir execução local e são sempre sobrescrevíveis.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_VOCABULARY_PATH = PACKAGE_DIR / "vocabulary" / "tags.json"
DEFAULT_KEYWORDS_PATH = PACKAGE_DIR / "vocabulary" / "keywords.json"


class Settings(BaseSettings):
    """Configuração do serviço, carregada de variáveis de ambiente e ``.env``."""

    model_config = SettingsConfigDict(
        env_prefix="IA_MCP_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------ backend
    backend_base_url: str = "http://localhost:8000"
    backend_timeout_seconds: float = Field(default=10.0, gt=0)
    backend_perfil: str = "mcp"
    backend_ator_id: int | None = None

    # --------------------------------------------------------------- provedor IA
    ai_provider: Literal["auto", "openai_compatible", "heuristic"] = "auto"
    ai_base_url: str = ""
    ai_api_key: str = ""
    ai_model: str = ""
    ai_timeout_seconds: float = Field(default=20.0, gt=0)

    # --------------------------------------------------------------- vocabulário
    vocabulary_path: Path = DEFAULT_VOCABULARY_PATH
    keywords_path: Path = DEFAULT_KEYWORDS_PATH

    # ------------------------------------------------------------------ serviço
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8100, gt=0, lt=65536)
    mcp_path: str = "/mcp"

    # ------------------------------------------------------------------- limites
    max_tags: int = Field(default=8, gt=0, le=50)
    min_tag_confidence: float = Field(default=0.35, ge=0, le=1)
    max_text_chars: int = Field(default=4000, gt=0)
    max_summary_chars: int = Field(default=600, gt=0)

    # ------------------------------------------------------------ observabilidade
    log_level: str = "INFO"
    log_text: bool = False

    @field_validator("backend_base_url")
    @classmethod
    def _strip_backend_url(cls, value: str) -> str:
        return value.strip().rstrip("/")

    @field_validator("ai_base_url")
    @classmethod
    def _strip_ai_url(cls, value: str) -> str:
        return value.strip().rstrip("/")

    @field_validator("mcp_path")
    @classmethod
    def _validate_mcp_path(cls, value: str) -> str:
        normalized = "/" + value.strip().strip("/")
        if normalized == "/":
            raise ValueError("mcp_path não pode ser a raiz '/'")
        return normalized

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        return value.strip().upper()


__all__ = ["DEFAULT_KEYWORDS_PATH", "DEFAULT_VOCABULARY_PATH", "Settings"]
