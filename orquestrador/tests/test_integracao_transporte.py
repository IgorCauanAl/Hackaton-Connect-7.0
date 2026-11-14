"""Transporte: validação de demanda, pass-through GET e frontend estático."""

from __future__ import annotations

from pathlib import Path

import httpx

from orquestrador.clients.backend import BackendClient
from orquestrador.clients.ia import IAClient
from orquestrador.config import Settings
from orquestrador.main import create_app
from tests.conftest import H_ADMIN, H_LOJISTA, chamar

VALIDACAO = {"status": "validado", "demanda_id": 10}


async def test_validar_demanda_repassa_ao_backend(montar_app) -> None:
    app, vistos, _ = montar_app(
        {("POST", "/api/admin/demandas/10/validar"): (200, VALIDACAO)}
    )

    resposta = await chamar(
        app, "POST", "/orquestracao/demandas/10/validar", headers=H_ADMIN
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["resultado"] == VALIDACAO
    assert corpo["orquestracao"]["etapas"][0]["etapa"] == "validacao_demanda"
    assert vistos[0].url.path == "/api/admin/demandas/10/validar"
    assert vistos[0].headers["x-perfil"] == "admin"


async def test_validar_demanda_fora_do_contrato_vira_502(montar_app) -> None:
    app, _, _ = montar_app(
        {("POST", "/api/admin/demandas/10/validar"): (200, {"ok": True})}
    )

    resposta = await chamar(
        app, "POST", "/orquestracao/demandas/10/validar", headers=H_ADMIN
    )

    assert resposta.status_code == 502
    assert resposta.json()["codigo"] == "contrato_invalido"


async def test_proxy_get_repassa_ator_e_query(montar_app) -> None:
    app, vistos, _ = montar_app(
        {("GET", "/api/admin/demandas"): (200, [{"id": 1}])}
    )

    resposta = await chamar(
        app,
        "GET",
        "/api/admin/demandas",
        params={"status": "validada"},
        headers=H_ADMIN,
    )

    assert resposta.status_code == 200
    assert resposta.json() == [{"id": 1}]
    assert vistos[0].url.path == "/api/admin/demandas"
    assert vistos[0].url.params["status"] == "validada"
    assert vistos[0].headers["x-perfil"] == "admin"


async def test_proxy_get_preserva_erro_do_backend(montar_app) -> None:
    app, _, _ = montar_app(
        {("GET", "/api/demandas/10"): (403, {"detail": "sem acesso"})}
    )

    resposta = await chamar(app, "GET", "/api/demandas/10", headers=H_LOJISTA)

    assert resposta.status_code == 403
    assert resposta.json()["detail"] == "sem acesso"


async def test_proxy_e_somente_get() -> None:
    app, _, _ = _app_sem_frontend()

    resposta = await chamar(
        app, "POST", "/api/lojistas", headers=H_ADMIN, corpo={}
    )

    assert resposta.status_code == 405


async def test_frontend_estatico_servido_quando_build_existe(
    tmp_path: Path,
) -> None:
    (tmp_path / "index.html").write_text("<h1>ORVYN</h1>", encoding="utf-8")
    (tmp_path / "chat.html").write_text("<h1>Chat</h1>", encoding="utf-8")
    app = create_app(
        Settings(_env_file=None, frontend_dir=tmp_path),
        backend_client=_backend_vazio(),
        ia_client=_ia_vazia(),
    )

    raiz = await chamar(app, "GET", "/", headers={})
    chat = await chamar(app, "GET", "/chat.html", headers={})
    ausente = await chamar(app, "GET", "/nao-existe", headers={})

    assert raiz.status_code == 200
    assert "ORVYN" in raiz.text
    assert chat.status_code == 200
    assert "Chat" in chat.text
    assert ausente.status_code == 404


async def test_frontend_nao_montado_quando_desabilitado() -> None:
    app, _, _ = _app_sem_frontend()

    resposta = await chamar(app, "GET", "/", headers={})

    assert resposta.status_code == 404


def _backend_vazio() -> BackendClient:
    return BackendClient(
        base_url="http://backend.local",
        timeout=5,
        transport=httpx.MockTransport(lambda request: httpx.Response(404)),
    )


def _ia_vazia() -> IAClient:
    return IAClient(
        base_url="http://ia.local",
        timeout=5,
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"tags": []})
        ),
    )


def _app_sem_frontend():
    return (
        create_app(
            Settings(_env_file=None, frontend_enabled=False),
            backend_client=_backend_vazio(),
            ia_client=_ia_vazia(),
        ),
        [],
        [],
    )
