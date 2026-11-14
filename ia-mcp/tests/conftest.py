"""Fixtures compartilhadas. Nenhum teste acessa rede real."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from ia_mcp.vocabulary.loader import Vocabulary

TAGS = [
    {
        "tag": "atendimento_whatsapp",
        "label": "Atendimento via WhatsApp",
        "keywords": ["whatsapp", "zap"],
    },
    {
        "tag": "automacao_atendimento",
        "label": "Automação de atendimento",
        "keywords": ["automatizar", "automacao", "bot"],
    },
    {
        "tag": "atendimento_fora_horario",
        "label": "Atendimento fora do horário",
        "keywords": ["fora do horario", "fora do expediente"],
    },
    {
        "tag": "conversao_vendas",
        "label": "Conversão de vendas",
        "keywords": ["conversao de vendas", "perco vendas"],
    },
    {"tag": "controle_estoque", "keywords": ["estoque"]},
    {"tag": "pagamentos", "keywords": ["pix", "pagamento"]},
]

KEYWORDS = {
    "atendimento_whatsapp": ["mensagem", "chat"],
    "nao_existe": ["ignorar"],
}

SAMPLE_TEXT = (
    "Tenho uma loja de roupas e perco muitas vendas porque não consigo "
    "responder no WhatsApp fora do horário. Quero automatizar o atendimento "
    "e melhorar a conversão de vendas."
)

EXPECTED_TAGS = {
    "atendimento_whatsapp",
    "automacao_atendimento",
    "atendimento_fora_horario",
    "conversao_vendas",
}


@pytest.fixture(autouse=True)
def _isolate_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Garante que variáveis do ambiente do desenvolvedor não afetem os testes."""

    for key in list(os.environ):
        if key.startswith("IA_MCP_"):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture
def tags_file(tmp_path: Path) -> Path:
    path = tmp_path / "tags.json"
    path.write_text(json.dumps({"tags": TAGS}, ensure_ascii=False), encoding="utf-8")
    return path


@pytest.fixture
def keywords_file(tmp_path: Path) -> Path:
    path = tmp_path / "keywords.json"
    path.write_text(json.dumps(KEYWORDS, ensure_ascii=False), encoding="utf-8")
    return path


@pytest.fixture
def vocabulary(tags_file: Path, keywords_file: Path) -> Vocabulary:
    return Vocabulary.from_file(tags_file, keywords_file)


@pytest.fixture
def sample_text() -> str:
    return SAMPLE_TEXT


@pytest.fixture
def expected_tags() -> set[str]:
    return set(EXPECTED_TAGS)
