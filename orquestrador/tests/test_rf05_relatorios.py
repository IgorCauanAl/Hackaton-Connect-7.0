"""ORQ-RF-05 — encaminhamento de oportunidades e relatórios."""

from __future__ import annotations

import pytest

from tests.conftest import (
    H_ADMIN,
    H_STARTUP,
    OPORTUNIDADES,
    RELATORIO,
    chamar,
    corpo_enviado,
)

ENCAMINHAMENTO = {"status": "sucesso", "relatorio_id": 3, "mensagem": "Encaminhada."}


async def test_admin_encaminha_e_confirma_vinculos(montar_app) -> None:
    app, vistos, _ = montar_app(
        {
            ("POST", "/api/admin/demandas/10/encaminhar"): (200, ENCAMINHAMENTO),
            ("GET", "/api/startups/1/oportunidades"): (200, OPORTUNIDADES),
            ("GET", "/api/relatorios/3"): (200, RELATORIO),
        }
    )

    resposta = await chamar(
        app,
        "POST",
        "/orquestracao/demandas/10/encaminhar",
        corpo={"startup_id": 1},
        headers=H_ADMIN,
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["resultado"]["relatorio_id"] == 3
    assert corpo["resultado"]["startup_id"] == 1
    assert corpo["resultado"]["relatorio"]["demanda_id"] == 10

    etapas = {e["etapa"]: e["status"] for e in corpo["orquestracao"]["etapas"]}
    assert etapas == {
        "encaminhamento": "ok",
        "confirmacao_oportunidade": "ok",
        "leitura_relatorio": "ok",
    }
    assert corpo["orquestracao"]["avisos"] == []

    assert [v.url.path for v in vistos] == [
        "/api/admin/demandas/10/encaminhar",
        "/api/startups/1/oportunidades",
        "/api/relatorios/3",
    ]
    assert corpo_enviado(vistos[0]) == {"startup_id": 1}
    assert vistos[0].headers["x-perfil"] == "admin"
    assert vistos[2].url.params["versao"] == "anonimizada"


async def test_nao_admin_nao_encaminha(montar_app) -> None:
    app, vistos, _ = montar_app(
        {("POST", "/api/admin/demandas/10/encaminhar"): (200, ENCAMINHAMENTO)}
    )

    resposta = await chamar(
        app,
        "POST",
        "/orquestracao/demandas/10/encaminhar",
        corpo={"startup_id": 1},
        headers=H_STARTUP,
    )

    assert resposta.status_code == 403
    assert resposta.json()["etapa"] == "autorizacao"
    assert vistos == []


async def test_relatorio_ausente_nas_oportunidades_gera_aviso(montar_app) -> None:
    app, _, _ = montar_app(
        {
            ("POST", "/api/admin/demandas/10/encaminhar"): (200, ENCAMINHAMENTO),
            ("GET", "/api/startups/1/oportunidades"): (200, []),
            ("GET", "/api/relatorios/3"): (200, RELATORIO),
        }
    )

    resposta = await chamar(
        app,
        "POST",
        "/orquestracao/demandas/10/encaminhar",
        corpo={"startup_id": 1},
        headers=H_ADMIN,
    )

    assert resposta.status_code == 200
    assert "relatorio_nao_listado" in {
        a["codigo"] for a in resposta.json()["orquestracao"]["avisos"]
    }


@pytest.mark.parametrize(
    "documento",
    [
        {**RELATORIO, "demanda_id": 99},
        {**RELATORIO, "startup_id": 99},
    ],
)
async def test_relatorio_de_outro_vinculo_vira_502(
    montar_app, documento: dict
) -> None:
    app, _, _ = montar_app(
        {
            ("POST", "/api/admin/demandas/10/encaminhar"): (200, ENCAMINHAMENTO),
            ("GET", "/api/startups/1/oportunidades"): (200, OPORTUNIDADES),
            ("GET", "/api/relatorios/3"): (200, documento),
        }
    )

    resposta = await chamar(
        app,
        "POST",
        "/orquestracao/demandas/10/encaminhar",
        corpo={"startup_id": 1},
        headers=H_ADMIN,
    )

    assert resposta.status_code == 502
    assert resposta.json()["codigo"] == "contrato_invalido"


async def test_encaminhamento_sem_relatorio_id_vira_502(montar_app) -> None:
    app, _, _ = montar_app(
        {
            ("POST", "/api/admin/demandas/10/encaminhar"): (
                200,
                {"status": "sucesso"},
            )
        }
    )

    resposta = await chamar(
        app,
        "POST",
        "/orquestracao/demandas/10/encaminhar",
        corpo={"startup_id": 1},
        headers=H_ADMIN,
    )

    assert resposta.status_code == 502
    assert resposta.json()["codigo"] == "contrato_invalido"


async def test_startup_lista_suas_oportunidades(montar_app) -> None:
    app, vistos, _ = montar_app(
        {("GET", "/api/startups/2/oportunidades"): (200, OPORTUNIDADES)}
    )

    resposta = await chamar(
        app, "GET", "/orquestracao/startups/2/relatorios", headers=H_STARTUP
    )

    assert resposta.status_code == 200
    assert resposta.json()["resultado"] == OPORTUNIDADES
    assert vistos[0].headers["x-ator-id"] == "2"


async def test_lista_fora_do_contrato_vira_502(montar_app) -> None:
    app, _, _ = montar_app(
        {("GET", "/api/startups/2/oportunidades"): (200, {"itens": []})}
    )

    resposta = await chamar(
        app, "GET", "/orquestracao/startups/2/relatorios", headers=H_STARTUP
    )

    assert resposta.status_code == 502
    assert resposta.json()["codigo"] == "contrato_invalido"


@pytest.mark.parametrize("versao", ["anonimizada", "completa"])
async def test_leitura_de_relatorio_por_versao(montar_app, versao: str) -> None:
    app, vistos, _ = montar_app(
        {("GET", "/api/relatorios/3"): (200, {**RELATORIO, "versao": versao})}
    )

    resposta = await chamar(
        app,
        "GET",
        "/orquestracao/relatorios/3",
        params={"versao": versao},
        headers=H_STARTUP,
    )

    assert resposta.status_code == 200
    assert resposta.json()["resultado"]["versao"] == versao
    assert vistos[0].url.params["versao"] == versao


async def test_versao_invalida_nao_chama_backend(montar_app) -> None:
    app, vistos, _ = montar_app({("GET", "/api/relatorios/3"): (200, RELATORIO)})

    resposta = await chamar(
        app,
        "GET",
        "/orquestracao/relatorios/3",
        params={"versao": "publica"},
        headers=H_STARTUP,
    )

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "requisicao_invalida"
    assert vistos == []
