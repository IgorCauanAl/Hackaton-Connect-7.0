"""Prompts usados pelo provedor OpenAI-compatible.

Os prompts pedem JSON estrito e delimitam a responsabilidade da IA: classificar,
resumir e interpretar. Quantidades, pesos de matching e status são
explicitamente proibidos.
"""

from __future__ import annotations

import json
from typing import Sequence

from ia_mcp.domain.models import GrupoInsight

CLASSIFICATION_SYSTEM = (
    "Você classifica demandas de varejo em tags de um vocabulário controlado. "
    "Responda SOMENTE com um objeto JSON no formato "
    '{"tags": ["tag_do_vocabulario"], "confidence": 0.0}. '
    "Use exclusivamente tags presentes no vocabulário informado. "
    "Não invente tags, não explique e não inclua texto fora do JSON."
)

SUMMARIZATION_SYSTEM = (
    "Você resume demandas de varejo em português do Brasil. "
    "Produza uma única frase objetiva, sem opinião, sem listas e sem markdown. "
    "Responda somente com o texto do resumo."
)

INSIGHTS_SYSTEM = (
    "Você interpreta grupos de demandas de varejo. "
    "Responda SOMENTE com um objeto JSON que mapeia a CHAVE de cada grupo para "
    "uma interpretação textual de uma frase, em português do Brasil. "
    "Inclua todos os grupos recebidos e não inclua contagens, quantidades, "
    "pesos, scores de matching, prioridades ou status."
)


def classification_user_prompt(text: str, tags: Sequence[str]) -> str:
    return json.dumps(
        {"vocabulario": list(tags), "texto": text},
        ensure_ascii=False,
    )


def summarization_user_prompt(text: str) -> str:
    return text


def insights_user_prompt(groups: Sequence[GrupoInsight]) -> str:
    payload = [
        {
            "chave": group.chave,
            "titulo": group.titulo,
            "quantidade": group.quantidade,
            "exemplos": list(group.exemplos),
        }
        for group in groups
    ]
    return json.dumps({"grupos": payload}, ensure_ascii=False)


__all__ = [
    "CLASSIFICATION_SYSTEM",
    "INSIGHTS_SYSTEM",
    "SUMMARIZATION_SYSTEM",
    "classification_user_prompt",
    "insights_user_prompt",
    "summarization_user_prompt",
]
