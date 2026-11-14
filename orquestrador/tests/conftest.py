"""Fixtures dos testes do orquestrador. Nenhum teste acessa rede real."""

from __future__ import annotations

import json
import os
from typing import Any, Callable

import httpx
import pytest

from orquestrador.clients.backend import BackendClient
from orquestrador.clients.ia import IAClient
from orquestrador.config import Settings
from orquestrador.main import create_app

H_LOJISTA = {"X-Perfil": "lojista", "X-Ator-Id": "1"}
H_ADMIN = {"X-Perfil": "admin"}
H_STARTUP = {"X-Perfil": "startup", "X-Ator-Id": "2"}

DEMANDA = {
    "lojista_id": 1,
    "respostas": {
        "objetivo": "vender_mais",
        "dificuldade": "atender_whatsapp",
        "canais": ["whatsapp"],
        "ferramentas": ["planilha"],
        "orcamento": "100_300",
        "urgencia": "ate_15_dias",
    },
    "texto_livre": "Não consigo responder no WhatsApp e perco vendas.",
}

RANKING = [
    {
        "startup_id": 1,
        "nome": "ZapBot",
        "indice": 91,
        "criterios": [{"criterio": "dor", "pontuacao": 95, "motivo": "match"}],
    }
]

REGISTRO = {
    "demanda_id": 10,
    "status": "sucesso",
    "tags_identificadas": ["whatsapp", "atendimento"],
    "tags_origem": "ia",
    "ranking_startups": RANKING,
    "mensagem": None,
}

RADAR = {
    "aviso": "Interpretação sugerida pela IA, sujeita à validação humana.",
    "radar": [
        {
            "grupo_id": 1,
            "titulo": "Atendimento",
            "quantidade": 7,
            "pontuacao": 100,
            "sugestao": "Dor recorrente de atendimento.",
            "origem": "ia",
            "destaque": True,
            "requer_validacao_humana": True,
        }
    ],
}

TESTE_REGISTRO = {
    "status": "sucesso",
    "teste_id": 7,
    "teste_status": "solicitado",
    "dias": 15,
    "mensagem": "Teste iniciado.",
}

TESTE_DETALHE = {
    "id": 7,
    "demanda_id": 10,
    "lojista_id": 1,
    "startup_id": 1,
    "status": "solicitado",
    "dias": 15,
}

RELATORIO = {
    "relatorio_id": 3,
    "demanda_id": 10,
    "startup_id": 1,
    "versao": "anonimizada",
    "blocos": {"resumo": {"resumo": "Atendimento"}},
}

OPORTUNIDADES = [
    {
        "relatorio_id": 3,
        "demanda_id": 10,
        "titulo": "Atendimento",
        "status": "encaminhada",
    }
]

MCP_RADAR = [
    {
        "dor": "Atendimento",
        "quantidade": 7,
        "sugestao_ia": "Automatizar o atendimento.",
        "origem": "ia",
    }
]

MCP_STARTUPS = [
    {
        "id": 1,
        "nome": "ZapBot",
        "descricao": "Atendimento automático",
        "solucao": "Bot de WhatsApp",
        "segmentos": ["moda"],
        "tags": ["whatsapp"],
    }
]


@pytest.fixture(autouse=True)
def _isolar_ambiente(monkeypatch: pytest.MonkeyPatch) -> None:
    for chave in list(os.environ):
        if chave.startswith("ORQ_"):
            monkeypatch.delenv(chave, raising=False)


def _handler_roteado(
    respostas: dict[tuple[str, str], tuple[int, Any]],
    vistos: list[httpx.Request],
) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        vistos.append(request)
        chave = (request.method, request.url.path)
        if chave not in respostas:
            return httpx.Response(
                404, json={"detail": f"rota não mapeada: {chave[0]} {chave[1]}"}
            )
        status, corpo = respostas[chave]
        return httpx.Response(status, json=corpo)

    return handler


@pytest.fixture
def montar_app():
    def _montar(
        respostas: dict[tuple[str, str], tuple[int, Any]] | None = None,
        *,
        ia: Callable[[httpx.Request], httpx.Response] | None = None,
        mcp: Any = None,
    ):
        vistos: list[httpx.Request] = []
        requisicoes_ia: list[httpx.Request] = []

        backend = BackendClient(
            base_url="http://backend.local",
            timeout=5,
            transport=httpx.MockTransport(
                _handler_roteado(respostas or {}, vistos)
            ),
        )

        handler_ia = ia or (
            lambda request: httpx.Response(200, json={"tags": ["whatsapp"]})
        )

        def registrando_ia(request: httpx.Request) -> httpx.Response:
            requisicoes_ia.append(request)
            return handler_ia(request)

        cliente_ia = IAClient(
            base_url="http://ia.local",
            timeout=5,
            transport=httpx.MockTransport(registrando_ia),
        )

        app = create_app(
            Settings(_env_file=None),
            backend_client=backend,
            ia_client=cliente_ia,
            mcp_client=mcp,
        )
        return app, vistos, requisicoes_ia

    return _montar


async def chamar(
    app,
    metodo: str,
    caminho: str,
    *,
    corpo: Any = None,
    headers: dict[str, str] | None = None,
    params: dict[str, str] | None = None,
) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://teste") as client:
        return await client.request(
            metodo,
            caminho,
            json=corpo,
            headers=headers if headers is not None else H_ADMIN,
            params=params,
        )


def corpo_enviado(request: httpx.Request) -> Any:
    return json.loads(request.content) if request.content else None
