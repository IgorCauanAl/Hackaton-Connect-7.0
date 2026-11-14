"""ORQ-RF-01/02 — fluxo de demandas e matching."""

from __future__ import annotations

import httpx
import pytest

from tests.conftest import (
    DEMANDA,
    H_LOJISTA,
    RANKING,
    REGISTRO,
    chamar,
    corpo_enviado,
)


async def test_classifica_antes_de_registrar_e_repassa_tags(montar_app) -> None:
    app, vistos, requisicoes_ia = montar_app(
        {("POST", "/api/demandas"): (201, REGISTRO)}
    )

    resposta = await chamar(
        app, "POST", "/orquestracao/demandas", corpo=DEMANDA, headers=H_LOJISTA
    )

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["resultado"]["demanda_id"] == 10

    etapas = {e["etapa"]: e["status"] for e in corpo["orquestracao"]["etapas"]}
    assert etapas == {"classificacao_ia": "ok", "registro_demanda": "ok"}
    assert corpo["orquestracao"]["avisos"] == []

    assert len(requisicoes_ia) == 1
    assert corpo_enviado(requisicoes_ia[0]) == {"texto": DEMANDA["texto_livre"]}

    assert len(vistos) == 1
    enviado = corpo_enviado(vistos[0])
    assert enviado["tags"] == ["whatsapp"]
    assert enviado["lojista_id"] == 1
    assert enviado["respostas"]["dificuldade"] == "atender_whatsapp"
    assert vistos[0].headers["x-perfil"] == "lojista"
    assert vistos[0].headers["x-ator-id"] == "1"


async def test_ia_indisponivel_deixa_backend_aplicar_fallback(montar_app) -> None:
    app, vistos, _ = montar_app(
        {("POST", "/api/demandas"): (201, REGISTRO)},
        ia=lambda request: httpx.Response(
            503, json={"detail": "Serviço de IA indisponível"}
        ),
    )

    resposta = await chamar(
        app, "POST", "/orquestracao/demandas", corpo=DEMANDA, headers=H_LOJISTA
    )

    assert resposta.status_code == 201
    corpo = resposta.json()
    etapas = {e["etapa"]: e["status"] for e in corpo["orquestracao"]["etapas"]}
    assert etapas["classificacao_ia"] == "falha"
    assert etapas["registro_demanda"] == "ok"
    assert "ia_indisponivel" in {a["codigo"] for a in corpo["orquestracao"]["avisos"]}
    assert "tags" not in corpo_enviado(vistos[0])


async def test_ia_sem_tags_aciona_fallback(montar_app) -> None:
    app, vistos, _ = montar_app(
        {("POST", "/api/demandas"): (201, REGISTRO)},
        ia=lambda request: httpx.Response(200, json={"tags": []}),
    )

    resposta = await chamar(
        app, "POST", "/orquestracao/demandas", corpo=DEMANDA, headers=H_LOJISTA
    )

    assert resposta.status_code == 201
    assert "classificacao_vazia" in {
        a["codigo"] for a in resposta.json()["orquestracao"]["avisos"]
    }
    assert "tags" not in corpo_enviado(vistos[0])


async def test_sem_match_e_sinalizado_sem_invalidar_fluxo(montar_app) -> None:
    sem_match = {**REGISTRO, "status": "sem_match", "ranking_startups": []}
    app, _, _ = montar_app({("POST", "/api/demandas"): (201, sem_match)})

    resposta = await chamar(
        app, "POST", "/orquestracao/demandas", corpo=DEMANDA, headers=H_LOJISTA
    )

    assert resposta.status_code == 201
    assert "sem_match" in {
        a["codigo"] for a in resposta.json()["orquestracao"]["avisos"]
    }


async def test_backend_5xx_vira_502_controlado(montar_app) -> None:
    app, _, _ = montar_app(
        {("POST", "/api/demandas"): (500, {"detail": "falha interna"})}
    )

    resposta = await chamar(
        app, "POST", "/orquestracao/demandas", corpo=DEMANDA, headers=H_LOJISTA
    )

    assert resposta.status_code == 502
    corpo = resposta.json()
    assert corpo["codigo"] == "backend_indisponivel"
    assert corpo["etapa"] == "registro_demanda"
    assert corpo["trace_id"] == resposta.headers["x-trace-id"]


async def test_regra_de_negocio_do_backend_e_repassada(montar_app) -> None:
    app, _, _ = montar_app(
        {
            ("POST", "/api/demandas"): (
                409,
                {"detail": "A demanda precisa estar validada."},
            )
        }
    )

    resposta = await chamar(
        app, "POST", "/orquestracao/demandas", corpo=DEMANDA, headers=H_LOJISTA
    )

    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "regra_de_negocio"
    assert resposta.json()["detail"] == "A demanda precisa estar validada."


@pytest.mark.parametrize(
    "registro_invalido",
    [
        {"status": "sucesso", "tags_identificadas": [], "ranking_startups": []},
        {**REGISTRO, "status": "desconhecido"},
        {**REGISTRO, "ranking_startups": "não é lista"},
        {**REGISTRO, "ranking_startups": []},
    ],
)
async def test_resposta_fora_do_contrato_vira_502(
    montar_app, registro_invalido: dict
) -> None:
    app, _, _ = montar_app(
        {("POST", "/api/demandas"): (201, registro_invalido)}
    )

    resposta = await chamar(
        app, "POST", "/orquestracao/demandas", corpo=DEMANDA, headers=H_LOJISTA
    )

    assert resposta.status_code == 502
    assert resposta.json()["codigo"] == "contrato_invalido"


async def test_matching_e_repassado_e_validado(montar_app) -> None:
    app, vistos, _ = montar_app(
        {
            ("GET", "/api/demandas/10/matching"): (
                200,
                {"demanda_id": 10, "sem_match": False, "ranking_startups": RANKING},
            )
        }
    )

    resposta = await chamar(
        app, "GET", "/orquestracao/demandas/10/matching", headers=H_LOJISTA
    )

    assert resposta.status_code == 200
    assert resposta.json()["resultado"]["ranking_startups"] == RANKING
    assert vistos[0].headers["x-perfil"] == "lojista"


async def test_matching_sem_match_com_ranking_gera_aviso(montar_app) -> None:
    app, _, _ = montar_app(
        {
            ("GET", "/api/demandas/10/matching"): (
                200,
                {"demanda_id": 10, "sem_match": True, "ranking_startups": RANKING},
            )
        }
    )

    resposta = await chamar(
        app, "GET", "/orquestracao/demandas/10/matching", headers=H_LOJISTA
    )

    assert resposta.status_code == 200
    assert "matching_inconsistente" in {
        a["codigo"] for a in resposta.json()["orquestracao"]["avisos"]
    }


async def test_matching_invalido_vira_502(montar_app) -> None:
    app, _, _ = montar_app(
        {("GET", "/api/demandas/10/matching"): (200, {"demanda_id": 10})}
    )

    resposta = await chamar(
        app, "GET", "/orquestracao/demandas/10/matching", headers=H_LOJISTA
    )

    assert resposta.status_code == 502
    assert resposta.json()["codigo"] == "contrato_invalido"
