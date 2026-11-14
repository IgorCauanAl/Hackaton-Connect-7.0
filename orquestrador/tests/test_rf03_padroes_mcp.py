"""Análise de padrões (tag derivada) e ferramentas MCP somente leitura."""

from __future__ import annotations

from typing import Any

import pytest

from tests.conftest import (
    H_ADMIN,
    H_LOJISTA,
    MCP_RADAR,
    MCP_STARTUPS,
    RADAR,
    chamar,
)

DEMANDAS_DO_GRUPO = [
    {"id": 10, "titulo": "Atendimento", "ramo": "moda", "status": "validada"}
]

DETALHE_DEMANDA = {
    "id": 10,
    "tags": ["whatsapp", "atendimento"],
    "tags_origem": "ia",
    "grupo_id": 1,
}


class FakeMCP:
    def __init__(self, respostas: dict[str, Any]) -> None:
        self._respostas = respostas
        self.chamadas: list[tuple[str, dict[str, Any] | None]] = []

    async def chamar(
        self, ferramenta: str, argumentos: dict[str, Any] | None = None
    ) -> Any:
        self.chamadas.append((ferramenta, argumentos))
        resposta = self._respostas[ferramenta]
        if isinstance(resposta, Exception):
            raise resposta
        return resposta


async def test_padroes_acrescenta_tag_derivada_das_demandas(montar_app) -> None:
    app, vistos, _ = montar_app(
        {
            ("GET", "/api/admin/radar"): (200, RADAR),
            ("GET", "/api/admin/radar/1/demandas"): (200, DEMANDAS_DO_GRUPO),
            ("GET", "/api/admin/demandas/10"): (200, DETALHE_DEMANDA),
        }
    )

    resposta = await chamar(app, "GET", "/orquestracao/padroes", headers=H_ADMIN)

    assert resposta.status_code == 200
    corpo = resposta.json()
    item = corpo["resultado"]["radar"][0]
    assert item["titulo"] == "Atendimento"
    assert item["tag"] == "whatsapp"
    assert item["quantidade"] == 7  # veio do backend, não foi recalculada
    caminhos = [v.url.path for v in vistos]
    assert caminhos == [
        "/api/admin/radar",
        "/api/admin/radar/1/demandas",
        "/api/admin/demandas/10",
    ]


async def test_padroes_sem_demandas_nao_quebra(montar_app) -> None:
    app, _, _ = montar_app(
        {
            ("GET", "/api/admin/radar"): (200, RADAR),
            ("GET", "/api/admin/radar/1/demandas"): (200, []),
        }
    )

    resposta = await chamar(app, "GET", "/orquestracao/padroes", headers=H_ADMIN)

    assert resposta.status_code == 200
    assert resposta.json()["resultado"]["radar"][0]["tag"] is None
    assert "tag_grupo_indisponivel" in {
        aviso["codigo"] for aviso in resposta.json()["orquestracao"]["avisos"]
    }


async def test_padroes_exige_admin(montar_app) -> None:
    app, vistos, _ = montar_app()

    resposta = await chamar(app, "GET", "/orquestracao/padroes", headers=H_LOJISTA)

    assert resposta.status_code == 403
    assert vistos == []


async def test_mcp_radar_repassa_resultado(montar_app) -> None:
    fake = FakeMCP({"listar_radar": MCP_RADAR})
    app, _, _ = montar_app(mcp=fake)

    resposta = await chamar(app, "GET", "/orquestracao/mcp/radar", headers=H_ADMIN)

    assert resposta.status_code == 200
    assert resposta.json()["resultado"] == MCP_RADAR
    assert fake.chamadas == [("listar_radar", None)]


async def test_mcp_startups_repassa_tag(montar_app) -> None:
    fake = FakeMCP({"buscar_startups": MCP_STARTUPS})
    app, _, _ = montar_app(mcp=fake)

    resposta = await chamar(
        app,
        "GET",
        "/orquestracao/mcp/startups",
        headers=H_ADMIN,
        params={"tag": "whatsapp"},
    )

    assert resposta.status_code == 200
    assert resposta.json()["resultado"] == MCP_STARTUPS
    assert fake.chamadas == [("buscar_startups", {"tag": "whatsapp"})]


async def test_mcp_sem_tag_nao_envia_argumento(montar_app) -> None:
    fake = FakeMCP({"buscar_startups": []})
    app, _, _ = montar_app(mcp=fake)

    await chamar(app, "GET", "/orquestracao/mcp/startups", headers=H_ADMIN)

    assert fake.chamadas == [("buscar_startups", {})]


@pytest.mark.parametrize(
    ("caminho", "resposta"),
    [
        ("/orquestracao/mcp/radar", {"listar_radar": {"nao": "lista"}}),
        (
            "/orquestracao/mcp/radar",
            {"listar_radar": [{"dor": "X", "quantidade": "7"}]},
        ),
        (
            "/orquestracao/mcp/startups",
            {"buscar_startups": [{"id": "1", "nome": "X"}]},
        ),
    ],
)
async def test_mcp_fora_do_contrato_vira_502(
    montar_app, caminho: str, resposta: dict[str, Any]
) -> None:
    app, _, _ = montar_app(mcp=FakeMCP(resposta))

    devolvida = await chamar(app, "GET", caminho, headers=H_ADMIN)

    assert devolvida.status_code == 502
    assert devolvida.json()["codigo"] == "contrato_invalido"


async def test_mcp_indisponivel_vira_503(montar_app) -> None:
    from orquestrador.errors import ServicoIndisponivel

    app, _, _ = montar_app(
        mcp=FakeMCP({"listar_radar": ServicoIndisponivel("sem MCP")})
    )

    resposta = await chamar(app, "GET", "/orquestracao/mcp/radar", headers=H_ADMIN)

    assert resposta.status_code == 503


async def test_mcp_exige_perfil_de_leitura(montar_app) -> None:
    fake = FakeMCP({"listar_radar": MCP_RADAR})
    app, _, _ = montar_app(mcp=fake)

    resposta = await chamar(app, "GET", "/orquestracao/mcp/radar", headers=H_LOJISTA)

    assert resposta.status_code == 403
    assert fake.chamadas == []
