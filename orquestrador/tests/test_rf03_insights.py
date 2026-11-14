"""ORQ-RF-03 — geração de insights e consulta do Radar."""

from __future__ import annotations

import pytest

from tests.conftest import H_ADMIN, H_LOJISTA, RADAR, chamar


async def test_admin_gera_insights(montar_app) -> None:
    app, vistos, requisicoes_ia = montar_app(
        {("POST", "/api/admin/insights/gerar"): (200, RADAR)}
    )

    resposta = await chamar(app, "POST", "/orquestracao/insights", headers=H_ADMIN)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["resultado"]["radar"][0]["grupo_id"] == 1

    etapas = {e["etapa"]: e["status"] for e in corpo["orquestracao"]["etapas"]}
    assert etapas == {"geracao_insights": "ok"}
    assert corpo["orquestracao"]["avisos"] == []

    # A IA é chamada pelo backend; o orquestrador não chama /ia/* diretamente.
    assert requisicoes_ia == []
    assert vistos[0].url.path == "/api/admin/insights/gerar"
    assert vistos[0].headers["x-perfil"] == "admin"


async def test_admin_consulta_radar(montar_app) -> None:
    app, vistos, _ = montar_app({("GET", "/api/admin/radar"): (200, RADAR)})

    resposta = await chamar(app, "GET", "/orquestracao/radar", headers=H_ADMIN)

    assert resposta.status_code == 200
    assert resposta.json()["resultado"] == RADAR
    assert vistos[0].url.path == "/api/admin/radar"


@pytest.mark.parametrize(
    ("metodo", "caminho"),
    [
        ("POST", "/orquestracao/insights"),
        ("GET", "/orquestracao/radar"),
    ],
)
async def test_nao_admin_recebe_403_sem_chamar_servicos(
    montar_app, metodo: str, caminho: str
) -> None:
    app, vistos, requisicoes_ia = montar_app(
        {
            ("POST", "/api/admin/insights/gerar"): (200, RADAR),
            ("GET", "/api/admin/radar"): (200, RADAR),
        }
    )

    resposta = await chamar(app, metodo, caminho, headers=H_LOJISTA)

    assert resposta.status_code == 403
    corpo = resposta.json()
    assert corpo["codigo"] == "acesso_negado"
    assert corpo["etapa"] == "autorizacao"
    assert vistos == []
    assert requisicoes_ia == []


async def test_fallback_de_referencia_e_sinalizado(montar_app) -> None:
    radar_referencia = {
        **RADAR,
        "radar": [{**RADAR["radar"][0], "origem": "referencia"}],
    }
    app, _, _ = montar_app(
        {("POST", "/api/admin/insights/gerar"): (200, radar_referencia)}
    )

    resposta = await chamar(app, "POST", "/orquestracao/insights", headers=H_ADMIN)

    assert resposta.status_code == 200
    assert "fallback_referencia" in {
        a["codigo"] for a in resposta.json()["orquestracao"]["avisos"]
    }


@pytest.mark.parametrize(
    "payload",
    [
        {"aviso": "ok"},
        {"radar": "não é lista"},
        {"radar": [{"grupo_id": 1, "titulo": "X"}]},
        {
            "radar": [
                {
                    **RADAR["radar"][0],
                    "quantidade": "7",
                }
            ]
        },
        {
            "radar": [
                {
                    **RADAR["radar"][0],
                    "sugestao": "   ",
                }
            ]
        },
    ],
)
async def test_radar_fora_do_contrato_vira_502(montar_app, payload: dict) -> None:
    app, _, _ = montar_app({("GET", "/api/admin/radar"): (200, payload)})

    resposta = await chamar(app, "GET", "/orquestracao/radar", headers=H_ADMIN)

    assert resposta.status_code == 502
    assert resposta.json()["codigo"] == "contrato_invalido"


async def test_ia_indisponivel_nao_vira_503_porque_backend_tem_fallback(
    montar_app,
) -> None:
    app, _, _ = montar_app(
        {("POST", "/api/admin/insights/gerar"): (200, RADAR)}
    )

    resposta = await chamar(app, "POST", "/orquestracao/insights", headers=H_ADMIN)

    assert resposta.status_code == 200
    assert resposta.json()["resultado"]["aviso"]
