"""Provedor de IA compatível com a API OpenAI (chat completions)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Sequence

import httpx

from ia_mcp.domain.models import (
    ClassificationOutcome,
    GrupoInsight,
    InsightsOutcome,
    SummaryOutcome,
)
from ia_mcp.errors import (
    ConfigurationError,
    InvalidProviderResponseError,
    ProviderUnavailableError,
)
from ia_mcp.providers.prompts import (
    CLASSIFICATION_SYSTEM,
    INSIGHTS_SYSTEM,
    SUMMARIZATION_SYSTEM,
    classification_user_prompt,
    insights_user_prompt,
    summarization_user_prompt,
)
from ia_mcp.vocabulary.loader import Vocabulary

logger = logging.getLogger(__name__)

_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def extract_json_object(content: str) -> dict[str, Any]:
    """Extrai o primeiro objeto JSON de uma resposta de modelo."""

    candidate = content.strip()
    fenced = _JSON_FENCE.search(candidate)
    if fenced:
        candidate = fenced.group(1).strip()

    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end <= start:
        raise InvalidProviderResponseError(
            "Resposta do provedor não contém um objeto JSON"
        )

    try:
        parsed = json.loads(candidate[start : end + 1])
    except json.JSONDecodeError as exc:
        raise InvalidProviderResponseError(
            f"Resposta do provedor não é JSON válido: {exc}"
        ) from exc

    if not isinstance(parsed, dict):
        raise InvalidProviderResponseError("Resposta do provedor não é um objeto JSON")
    return parsed


class OpenAICompatibleProvider:
    """Provedor que conversa com qualquer endpoint ``/chat/completions``."""

    name = "configured_model"

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str = "",
        timeout: float = 20.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not base_url:
            raise ConfigurationError("IA_MCP_AI_BASE_URL não configurada")
        if not model:
            raise ConfigurationError("IA_MCP_AI_MODEL não configurado")
        self._base_url = base_url.rstrip("/") + "/"
        self._model = model
        self._api_key = api_key
        self._timeout = timeout
        self._transport = transport

    async def _chat(self, system: str, user: str) -> str:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        payload = {
            "model": self._model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }

        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                transport=self._transport,
                headers=headers,
            ) as client:
                response = await client.post("chat/completions", json=payload)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ProviderUnavailableError("Timeout ao chamar o provedor de IA") from exc
        except httpx.HTTPStatusError as exc:
            raise ProviderUnavailableError(
                f"Provedor de IA respondeu HTTP {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError(
                f"Falha de comunicação com o provedor de IA: {exc}"
            ) from exc

        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise InvalidProviderResponseError(
                "Estrutura de resposta do provedor de IA é inválida"
            ) from exc

        if not isinstance(content, str) or not content.strip():
            raise InvalidProviderResponseError("Provedor de IA retornou conteúdo vazio")
        return content

    async def _chat_json(self, system: str, user: str) -> dict[str, Any]:
        return extract_json_object(await self._chat(system, user))

    async def classify(
        self, text: str, vocabulary: Vocabulary
    ) -> ClassificationOutcome:
        data = await self._chat_json(
            CLASSIFICATION_SYSTEM,
            classification_user_prompt(text, sorted(vocabulary.tags)),
        )

        raw_tags = data.get("tags")
        if not isinstance(raw_tags, list):
            raise InvalidProviderResponseError(
                "Resposta de classificação não contém a lista 'tags'"
            )

        tags: list[str] = []
        for item in raw_tags:
            if not isinstance(item, str):
                continue
            tag = item.strip()
            if tag in vocabulary and tag not in tags:
                tags.append(tag)

        if not tags:
            raise InvalidProviderResponseError(
                "Provedor não retornou nenhuma tag do vocabulário"
            )

        raw_confidence = data.get("confidence", 0.5)
        try:
            confidence = float(raw_confidence)
        except (TypeError, ValueError):
            confidence = 0.5
        confidence = min(1.0, max(0.0, confidence))

        return ClassificationOutcome(
            tags=tags,
            confidence=confidence,
            provider=self.name,
        )

    async def summarize(self, text: str) -> SummaryOutcome:
        content = await self._chat(SUMMARIZATION_SYSTEM, summarization_user_prompt(text))
        resumo = " ".join(content.split())
        if not resumo:
            raise InvalidProviderResponseError("Provedor retornou resumo vazio")
        return SummaryOutcome(resumo=resumo, provider=self.name)

    async def interpret(
        self, groups: Sequence[GrupoInsight]
    ) -> InsightsOutcome:
        if not groups:
            return InsightsOutcome(interpretacoes={}, provider=self.name)

        data = await self._chat_json(
            INSIGHTS_SYSTEM, insights_user_prompt(groups)
        )
        mapping = data.get("interpretacoes", data)
        if not isinstance(mapping, dict):
            raise InvalidProviderResponseError(
                "Resposta de insights não é um objeto JSON mapeando grupos"
            )

        interpretacoes: dict[str, str] = {}
        for group in groups:
            value = mapping.get(group.id)
            if not isinstance(value, str) or not value.strip():
                raise InvalidProviderResponseError(
                    f"Interpretação ausente para o grupo '{group.id}'"
                )
            interpretacoes[group.id] = " ".join(value.split())

        return InsightsOutcome(
            interpretacoes=interpretacoes,
            provider=self.name,
        )


__all__ = ["OpenAICompatibleProvider", "extract_json_object"]
