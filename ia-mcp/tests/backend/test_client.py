"""Testes do cliente HTTP do backend operacional (pass-through)."""

from __future__ import annotations

import httpx
import pytest

from ia_mcp.backend.client import BackendClient
from ia_mcp.errors import BackendUnavailableError, ConfigurationError

RADAR_PAYLOAD = {"items": [{"id": "r1", "titulo": "Oportunidade"}], "total": 1}
STARTUPS_PAYLOAD = [{"id": "s1", "nome": "Startup X"}]


def make_client(handler, *, base_url: str = "http://backend.local") -> BackendClient:
    return BackendClient(
        base_url=base_url,
        timeout=5,
        transport=httpx.MockTransport(handler),
    )


async def test_listar_radar_is_pass_through() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=RADAR_PAYLOAD)

    payload = await make_client(handler).listar_radar()

    assert payload == RADAR_PAYLOAD
    assert len(seen) == 1
    assert seen[0].method == "GET"
    assert seen[0].url.path == "/api/mcp/radar"
    assert seen[0].headers["x-perfil"] == "mcp"
    assert "x-ator-id" not in seen[0].headers


async def test_buscar_startups_sends_filters() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=STARTUPS_PAYLOAD)

    payload = await make_client(handler).buscar_startups(tag="whatsapp", segmento="moda")

    assert payload == STARTUPS_PAYLOAD
    assert seen[0].method == "GET"
    assert seen[0].url.path == "/api/mcp/startups"
    assert dict(seen[0].url.params) == {"tag": "whatsapp", "segmento": "moda"}


async def test_buscar_startups_without_filters_sends_no_query() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=STARTUPS_PAYLOAD)

    await make_client(handler).buscar_startups(tag="  ", segmento=None)

    assert dict(seen[0].url.params) == {}


async def test_http_error_becomes_backend_unavailable() -> None:
    client = make_client(lambda request: httpx.Response(404, text="não encontrado"))

    with pytest.raises(BackendUnavailableError):
        await client.listar_radar()


async def test_timeout_becomes_backend_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    with pytest.raises(BackendUnavailableError):
        await make_client(handler).listar_radar()


async def test_invalid_json_becomes_backend_unavailable() -> None:
    client = make_client(lambda request: httpx.Response(200, text="<html>erro</html>"))

    with pytest.raises(BackendUnavailableError):
        await client.buscar_startups()


def test_requires_base_url() -> None:
    with pytest.raises(ConfigurationError):
        BackendClient(base_url="")


async def test_sends_configured_actor_headers() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=RADAR_PAYLOAD)

    client = BackendClient(
        base_url="http://backend.local",
        perfil="mcp",
        ator_id=42,
        transport=httpx.MockTransport(handler),
    )

    await client.listar_radar()

    assert seen[0].headers["x-perfil"] == "mcp"
    assert seen[0].headers["x-ator-id"] == "42"
