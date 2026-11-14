"""Configuração do orquestrador.

Tudo vem de variáveis de ambiente com prefixo ``ORQ_``. Nenhuma URL, credencial
ou caminho fixo no código.
"""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração carregada do ambiente e de ``.env``."""

    model_config = SettingsConfigDict(
        env_prefix="ORQ_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------ backend
    backend_base_url: str = "http://localhost:8000"
    backend_timeout_seconds: float = Field(default=10.0, gt=0)

    # ----------------------------------------------------------------- IA/MCP
    # Precisa acomodar o modelo de IA configurado no IA/MCP (20s por padrão).
    ia_base_url: str = "http://localhost:8100"
    ia_timeout_seconds: float = Field(default=25.0, gt=0)

    # ------------------------------------------------------------------ serviço
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8200, gt=0, lt=65536)

    # ------------------------------------------------------------ observabilidade
    idempotency_ttl_seconds: float = Field(default=600.0, ge=0)
    log_level: str = "INFO"

    @field_validator("backend_base_url", "ia_base_url")
    @classmethod
    def _normalizar_url(cls, value: str) -> str:
        normalizada = value.strip().rstrip("/")
        if not normalizada:
            raise ValueError("URL base não pode ser vazia")
        return normalizada

    @field_validator("log_level")
    @classmethod
    def _normalizar_log_level(cls, value: str) -> str:
        return value.strip().upper()


__all__ = ["Settings"]
