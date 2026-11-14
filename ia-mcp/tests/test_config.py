"""Testes de configuração e construção da cadeia de provedores."""

from __future__ import annotations

import pytest

from ia_mcp.config import DEFAULT_KEYWORDS_PATH, DEFAULT_VOCABULARY_PATH, Settings
from ia_mcp.errors import ConfigurationError
from ia_mcp.main import build_provider_chain, load_vocabulary
from ia_mcp.providers.heuristic import HeuristicProvider
from ia_mcp.providers.openai_compatible import OpenAICompatibleProvider


def test_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.ai_provider == "auto"
    assert settings.mcp_path == "/mcp"
    assert settings.backend_base_url == "http://localhost:8000"
    assert settings.max_tags == 8
    assert settings.vocabulary_path == DEFAULT_VOCABULARY_PATH
    assert settings.keywords_path == DEFAULT_KEYWORDS_PATH


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IA_MCP_BACKEND_BASE_URL", "https://api.exemplo.com/")
    monkeypatch.setenv("IA_MCP_MAX_TAGS", "3")
    monkeypatch.setenv("IA_MCP_AI_PROVIDER", "heuristic")

    settings = Settings(_env_file=None)

    assert settings.backend_base_url == "https://api.exemplo.com"
    assert settings.max_tags == 3
    assert settings.ai_provider == "heuristic"


@pytest.mark.parametrize("value", ["mcp", "mcp/", "/mcp/", " /mcp "])
def test_mcp_path_normalization(value: str) -> None:
    assert Settings(_env_file=None, mcp_path=value).mcp_path == "/mcp"


def test_mcp_path_rejects_root() -> None:
    with pytest.raises(ValueError):
        Settings(_env_file=None, mcp_path="/")


def test_heuristic_mode_only_uses_heuristic() -> None:
    chain = build_provider_chain(Settings(_env_file=None, ai_provider="heuristic"))

    assert len(chain.providers) == 1
    assert isinstance(chain.providers[0], HeuristicProvider)


def test_auto_without_model_uses_heuristic() -> None:
    settings = Settings(
        _env_file=None,
        ai_provider="auto",
        ai_base_url="",
        ai_model="",
    )

    chain = build_provider_chain(settings)

    assert [provider.name for provider in chain.providers] == ["heuristic_fallback"]


def test_auto_with_model_uses_llm_then_heuristic() -> None:
    settings = Settings(
        _env_file=None,
        ai_provider="auto",
        ai_base_url="https://api.exemplo.com/v1",
        ai_model="modelo",
    )

    chain = build_provider_chain(settings)

    assert len(chain.providers) == 2
    assert isinstance(chain.providers[0], OpenAICompatibleProvider)
    assert isinstance(chain.providers[1], HeuristicProvider)


def test_explicit_llm_without_credentials_fails() -> None:
    settings = Settings(
        _env_file=None,
        ai_provider="openai_compatible",
        ai_base_url="",
        ai_model="",
    )

    with pytest.raises(ConfigurationError):
        build_provider_chain(settings)


def test_default_vocabulary_files_load() -> None:
    vocabulary = load_vocabulary(Settings(_env_file=None))

    assert len(vocabulary) > 0
    assert "atendimento_whatsapp" in vocabulary
