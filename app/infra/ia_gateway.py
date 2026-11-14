"""Porta (Protocol) + adaptadores para o módulo de IA/MCP, feito por outra pessoa.

O backend depende só de `IAGateway`. Contrato HTTP esperado do colega (JSON):
  POST {IA_URL}/ia/classificar  {"texto": str}               -> {"tags": [str]}
  POST {IA_URL}/ia/resumir      {"texto": str}               -> {"resumo": str}
  POST {IA_URL}/ia/insights     {"grupos": [{"chave","titulo","quantidade","exemplos"}]}
                                                              -> {"interpretacoes": {chave: str}}
"""
from __future__ import annotations

import json
import urllib.request
from typing import Protocol, Sequence

from app.core.errors import IAIndisponivel


class IAGateway(Protocol):
    def extrair_tags(self, texto: str) -> list[str]: ...
    def resumir(self, texto: str) -> str: ...
    def interpretar_grupos(self, grupos: Sequence[dict]) -> dict[str, str]: ...


class HttpIAGateway:
    def __init__(self, base_url: str, timeout: float = 2.0):
        self._base = base_url.rstrip("/")
        self._timeout = timeout

    def _post(self, caminho: str, corpo: dict) -> dict:
        req = urllib.request.Request(
            f"{self._base}{caminho}", data=json.dumps(corpo).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # rede, timeout, JSON inválido...
            raise IAIndisponivel(str(exc)) from exc

    def extrair_tags(self, texto: str) -> list[str]:
        return list(self._post("/ia/classificar", {"texto": texto})["tags"])

    def resumir(self, texto: str) -> str:
        return str(self._post("/ia/resumir", {"texto": texto})["resumo"])

    def interpretar_grupos(self, grupos: Sequence[dict]) -> dict[str, str]:
        return dict(self._post("/ia/insights", {"grupos": list(grupos)})["interpretacoes"])


class IAIndisponivelGateway:
    """Null Object: IA não configurada. Força os fallbacks (útil na demo e nos testes)."""

    def extrair_tags(self, texto):
        raise IAIndisponivel("IA não configurada")

    def resumir(self, texto):
        raise IAIndisponivel("IA não configurada")

    def interpretar_grupos(self, grupos):
        raise IAIndisponivel("IA não configurada")
