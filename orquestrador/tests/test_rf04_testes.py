"""ORQ-RF-04 — ciclo de teste demonstrativo."""

from __future__ import annotations

import pytest

from tests.conftest import (
    H_ADMIN,
    H_LOJISTA,
    TESTE_DETALHE,
    TESTE_REGISTRO,
    chamar,
    corpo_enviado,
)

TESTE = {"demanda_id": 10, "startup_id": 1, "autorizacao": True}


async def test_lojista_solicita_teste_e_status_e_confirmado(montar_app) -> None:
    app, vistos, _ = montar_app(
        {
            ("POST", "/api/testes"): (201, TESTE_REGISTRO),
            ("GET", "/api/testes/7"): (200, TESTE_DETALHE),
        }
    )

    resposta = await chamar(
        app, "POST", "/orquestracao/testes", corpo=TESTE, headers=H_LOJISTA
    )

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["resultado"]["teste_id"] == 7
    assert corpo["teste"]["id"] == 7

    etapas = {e["etapa"]: e["status"] for e in corpo["orquestracao"]["etapas"]}
    assert etapas == {"registro_teste": "ok", "confirmacao_status": "ok"}
    assert corpo["orquestracao"]["avisos"] == []

    assert [v.url.path for v in vistos] == ["/api/testes", "/api/testes/7"]
    assert corpo_enviado(vistos[0]) == TESTE
    assert vistos[0].headers["x-perfil"] == "lojista"


async def test_sem_autorizacao_expressa_nao_chama_backend(montar_app) -> None:
    app, vistos, _ = montar_app(
        {("POST", "/api/testes"): (201, TESTE_REGISTRO)}
    )

    resposta = await chamar(
        app,
        "POST",
        "/orquestracao/testes",
        corpo={**TESTE, "autorizacao": False},
        headers=H_LOJISTA,
    )

    assert resposta.status_code == 409
    corpo = resposta.json()
    assert corpo["codigo"] == "regra_de_negocio"
    assert corpo["etapa"] == "autorizacao"
    assert vistos == []


async def test_perfil_diferente_de_lojista_recebe_403(montar_app) -> None:
    app, vistos, _ = montar_app(
        {("POST", "/api/testes"): (201, TESTE_REGISTRO)}
    )

    resposta = await chamar(
        app, "POST", "/orquestracao/testes", corpo=TESTE, headers=H_ADMIN
    )

    assert resposta.status_code == 403
    assert resposta.json()["etapa"] == "autorizacao"
    assert vistos == []


async def test_status_divergente_gera_aviso_mas_nao_falha(montar_app) -> None:
    detalhe = {**TESTE_DETALHE, "status": "em_andamento"}
    app, _, _ = montar_app(
        {
            ("POST", "/api/testes"): (201, TESTE_REGISTRO),
            ("GET", "/api/testes/7"): (200, detalhe),
        }
    )

    resposta = await chamar(
        app, "POST", "/orquestracao/testes", corpo=TESTE, headers=H_LOJISTA
    )

    assert resposta.status_code == 201
    assert "status_divergente" in {
        a["codigo"] for a in resposta.json()["orquestracao"]["avisos"]
    }


async def test_consulta_de_teste_valida_o_id(montar_app) -> None:
    app, _, _ = montar_app({("GET", "/api/testes/7"): (200, TESTE_DETALHE)})

    ok = await chamar(app, "GET", "/orquestracao/testes/7", headers=H_LOJISTA)
    assert ok.status_code == 200
    assert ok.json()["resultado"]["id"] == 7


async def test_consulta_de_outro_teste_vira_502(montar_app) -> None:
    app, _, _ = montar_app(
        {("GET", "/api/testes/7"): (200, {**TESTE_DETALHE, "id": 99})}
    )

    resposta = await chamar(
        app, "GET", "/orquestracao/testes/7", headers=H_LOJISTA
    )

    assert resposta.status_code == 502
    assert resposta.json()["codigo"] == "contrato_invalido"


async def test_feedback_demo_e_confirmado(montar_app) -> None:
    feedback = {
        "status": "sucesso",
        "teste_id": 7,
        "feedback_demo_id": 2,
        "mensagem": "Feedback registrado.",
    }
    app, vistos, _ = montar_app(
        {("POST", "/api/testes/7/feedback-demo"): (200, feedback)}
    )

    resposta = await chamar(
        app, "POST", "/orquestracao/testes/7/feedback", headers=H_LOJISTA
    )

    assert resposta.status_code == 200
    assert resposta.json()["resultado"]["teste_id"] == 7
    assert vistos[0].url.path == "/api/testes/7/feedback-demo"


async def test_feedback_de_outro_teste_vira_502(montar_app) -> None:
    app, _, _ = montar_app(
        {
            ("POST", "/api/testes/7/feedback-demo"): (
                200,
                {"status": "sucesso", "teste_id": 99},
            )
        }
    )

    resposta = await chamar(
        app, "POST", "/orquestracao/testes/7/feedback", headers=H_LOJISTA
    )

    assert resposta.status_code == 502
    assert resposta.json()["codigo"] == "contrato_invalido"


@pytest.mark.parametrize(
    "registro_invalido",
    [
        {"status": "sucesso", "teste_status": "solicitado"},
        {"status": "sucesso", "teste_id": "7", "teste_status": "solicitado"},
        {"status": "sucesso", "teste_id": 7},
    ],
)
async def test_registro_fora_do_contrato_vira_502(
    montar_app, registro_invalido: dict
) -> None:
    app, _, _ = montar_app(
        {("POST", "/api/testes"): (201, registro_invalido)}
    )

    resposta = await chamar(
        app, "POST", "/orquestracao/testes", corpo=TESTE, headers=H_LOJISTA
    )

    assert resposta.status_code == 502
    assert resposta.json()["codigo"] == "contrato_invalido"
