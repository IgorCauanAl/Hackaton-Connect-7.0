"""Testes transversais: infraestrutura, erros e idempotência."""

from __future__ import annotations

import httpx
import pytest

from orquestrador.clients.backend import BackendClient
from orquestrador.clients.ia import IAClient
from orquestrador.config import Settings
from orquestrador.main import create_app
from tests.conftest import (
    DEMANDA,
    H_ADMIN,
    H_LOJISTA,
    REGISTRO,
    chamar,
    corpo_enviado,
)


async def test_health(montar_app) -> None:
    app, vistos, requisicoes_ia = montar_app()

    resposta = await chamar(app, "GET", "/health", headers={})

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "servico": "orquestrador"}
    assert vistos == []
    assert requisicoes_ia == []


async def test_trace_id_em_sucesso_e_em_erro(montar_app) -> None:
    app, _, _ = montar_app(
        {("POST", "/api/demandas"): (201, REGISTRO)}
    )

    ok = await chamar(
        app, "POST", "/orquestracao/demandas", corpo=DEMANDA, headers=H_LOJISTA
    )
    assert ok.headers["x-trace-id"]

    erro = await chamar(app, "GET", "/orquestracao/radar", headers=H_LOJISTA)
    assert erro.status_code == 403
    assert erro.json()["trace_id"] == erro.headers["x-trace-id"]


async def test_trace_id_do_cliente_nao_e_confiado(montar_app) -> None:
    app, _, _ = montar_app()

    primeira = await chamar(app, "GET", "/health", headers={})
    segunda = await chamar(app, "GET", "/health", headers={})

    assert primeira.headers["x-trace-id"] != segunda.headers["x-trace-id"]


async def test_perfil_ausente_vira_422(montar_app) -> None:
    app, vistos, _ = montar_app()

    resposta = await chamar(app, "GET", "/orquestracao/radar", headers={})

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "requisicao_invalida"
    assert vistos == []


async def test_perfil_invalido_vira_401(montar_app) -> None:
    app, vistos, _ = montar_app()

    resposta = await chamar(
        app, "GET", "/orquestracao/radar", headers={"X-Perfil": "root"}
    )

    assert resposta.status_code == 401
    assert resposta.json()["codigo"] == "ator_invalido"
    assert vistos == []


async def test_ator_id_invalido_vira_422(montar_app) -> None:
    app, vistos, _ = montar_app()

    resposta = await chamar(
        app,
        "GET",
        "/orquestracao/radar",
        headers={"X-Perfil": "admin", "X-Ator-Id": "0"},
    )

    assert resposta.status_code == 422
    assert vistos == []


async def test_payload_invalido_vira_422_sem_chamar_servicos(montar_app) -> None:
    app, vistos, requisicoes_ia = montar_app()

    resposta = await chamar(
        app,
        "POST",
        "/orquestracao/demandas",
        corpo={"lojista_id": 1},
        headers=H_LOJISTA,
    )

    assert resposta.status_code == 422
    assert resposta.json()["etapa"] == "validacao"
    assert vistos == []
    assert requisicoes_ia == []


async def test_rota_inexistente_usa_o_mesmo_envelope(montar_app) -> None:
    app, _, _ = montar_app()

    resposta = await chamar(app, "GET", "/orquestracao/nao-existe", headers=H_ADMIN)

    assert resposta.status_code == 404
    corpo = resposta.json()
    assert corpo["codigo"] == "nao_encontrado"
    assert "trace_id" in corpo


async def test_idempotency_key_replay_nao_duplica_operacao(montar_app) -> None:
    app, vistos, requisicoes_ia = montar_app(
        {("POST", "/api/demandas"): (201, REGISTRO)}
    )
    headers = {**H_LOJISTA, "Idempotency-Key": "abc-123"}

    primeira = await chamar(
        app, "POST", "/orquestracao/demandas", corpo=DEMANDA, headers=headers
    )
    segunda = await chamar(
        app, "POST", "/orquestracao/demandas", corpo=DEMANDA, headers=headers
    )

    assert primeira.status_code == 201
    assert segunda.status_code == 201
    assert primeira.json() == segunda.json()
    assert segunda.headers.get("x-idempotente-replay") == "true"
    assert len(vistos) == 1
    assert len(requisicoes_ia) == 1


async def test_idempotency_key_com_corpo_diferente_vira_409(montar_app) -> None:
    app, vistos, _ = montar_app(
        {("POST", "/api/demandas"): (201, REGISTRO)}
    )
    headers = {**H_LOJISTA, "Idempotency-Key": "abc-123"}

    await chamar(
        app, "POST", "/orquestracao/demandas", corpo=DEMANDA, headers=headers
    )
    outra = {**DEMANDA, "texto_livre": "Outro texto completamente diferente."}
    resposta = await chamar(
        app, "POST", "/orquestracao/demandas", corpo=outra, headers=headers
    )

    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "idempotency_conflict"
    assert len(vistos) == 1


async def test_sem_idempotency_key_cada_chamada_executa(montar_app) -> None:
    app, vistos, _ = montar_app(
        {("POST", "/api/demandas"): (201, REGISTRO)}
    )

    await chamar(
        app, "POST", "/orquestracao/demandas", corpo=DEMANDA, headers=H_LOJISTA
    )
    await chamar(
        app, "POST", "/orquestracao/demandas", corpo=DEMANDA, headers=H_LOJISTA
    )

    assert len(vistos) == 2


async def test_timeout_do_backend_vira_503() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("estourou", request=request)

    app = create_app(
        Settings(_env_file=None),
        backend_client=BackendClient(
            base_url="http://backend.local",
            timeout=0.1,
            transport=httpx.MockTransport(handler),
        ),
        ia_client=IAClient(
            base_url="http://ia.local",
            timeout=0.1,
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json={"tags": ["whatsapp"]})
            ),
        ),
    )

    resposta = await chamar(
        app, "POST", "/orquestracao/demandas", corpo=DEMANDA, headers=H_LOJISTA
    )

    assert resposta.status_code == 503
    assert resposta.json()["codigo"] == "backend_timeout"
    assert resposta.json()["etapa"] == "registro_demanda"


async def test_timeout_da_ia_aciona_fallback(montar_app) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("estourou", request=request)

    app, vistos, _ = montar_app(
        {("POST", "/api/demandas"): (201, REGISTRO)}, ia=handler
    )

    resposta = await chamar(
        app, "POST", "/orquestracao/demandas", corpo=DEMANDA, headers=H_LOJISTA
    )

    assert resposta.status_code == 201
    assert "ia_indisponivel" in {
        a["codigo"] for a in resposta.json()["orquestracao"]["avisos"]
    }
    assert "tags" not in corpo_enviado(vistos[0])


@pytest.mark.parametrize(
    ("status", "codigo"),
    [
        (401, "ator_invalido"),
        (403, "acesso_negado"),
        (404, "nao_encontrado"),
        (409, "regra_de_negocio"),
        (422, "requisicao_invalida"),
    ],
)
async def test_4xx_do_backend_preserva_status_e_codigo(
    montar_app, status: int, codigo: str
) -> None:
    app, _, _ = montar_app(
        {("POST", "/api/demandas"): (status, {"detail": "motivo"})}
    )

    resposta = await chamar(
        app, "POST", "/orquestracao/demandas", corpo=DEMANDA, headers=H_LOJISTA
    )

    assert resposta.status_code == status
    assert resposta.json()["codigo"] == codigo
    assert resposta.json()["detail"] == "motivo"


async def test_json_invalido_do_backend_vira_502(montar_app) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>ops</html>")

    app, _, _ = montar_app()
    # Substitui o transporte do backend já montado por um que devolve HTML.
    app.state.container.demandas._backend._transport = httpx.MockTransport(handler)

    resposta = await chamar(
        app, "POST", "/orquestracao/demandas", corpo=DEMANDA, headers=H_LOJISTA
    )

    assert resposta.status_code == 502
    assert resposta.json()["codigo"] == "contrato_invalido"
