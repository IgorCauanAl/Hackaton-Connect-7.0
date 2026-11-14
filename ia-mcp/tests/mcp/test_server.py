"""Testes das ferramentas MCP e do pass-through para a API do backend."""

from __future__ import annotations

import json

import httpx
import pytest
from fastmcp.exceptions import ToolError

from ia_mcp.backend.client import BackendClient
from ia_mcp.mcp.server import create_mcp_server

RADAR_PAYLOAD = {"items": [{"id": "r1"}], "total": 1}
STARTUPS_PAYLOAD = [{"id": "s1", "nome": "Startup X"}]


def make_server(handler) -> tuple[object, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def recording_handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    client = BackendClient(
        base_url="http://backend.local",
        timeout=5,
        transport=httpx.MockTransport(recording_handler),
    )
    return create_mcp_server(client), seen


async def test_exposes_exactly_two_read_only_tools() -> None:
    server, _ = make_server(lambda request: httpx.Response(200, json={}))

    tools = await server.list_tools()

    assert {tool.name for tool in tools} == {"listar_radar", "buscar_startups"}
    for tool in tools:
        assert tool.annotations is not None
        assert tool.annotations.read_only_hint is True
        assert tool.annotations.destructive_hint is False


async def test_buscar_startups_schema_has_tag_and_segmento() -> None:
    server, _ = make_server(lambda request: httpx.Response(200, json={}))

    tools = {tool.name: tool for tool in await server.list_tools()}
    properties = tools["buscar_startups"].parameters["properties"]

    assert set(properties) == {"tag", "segmento"}


async def test_listar_radar_returns_backend_payload_unchanged() -> None:
    server, seen = make_server(lambda request: httpx.Response(200, json=RADAR_PAYLOAD))

    result = await server.call_tool("listar_radar", {})

    assert result.is_error is False
    assert result.structured_content == RADAR_PAYLOAD
    assert seen[0].method == "GET"
    assert seen[0].url.path == "/api/mcp/radar"


async def test_buscar_startups_returns_list_payload_and_sends_filters() -> None:
    server, seen = make_server(
        lambda request: httpx.Response(200, json=STARTUPS_PAYLOAD)
    )

    result = await server.call_tool(
        "buscar_startups", {"tag": "whatsapp", "segmento": "moda"}
    )

    assert result.is_error is False
    assert json.loads(result.content[0].text) == STARTUPS_PAYLOAD
    assert dict(seen[0].url.params) == {"tag": "whatsapp", "segmento": "moda"}


async def test_backend_error_becomes_tool_error() -> None:
    server, _ = make_server(lambda request: httpx.Response(500, text="erro"))

    with pytest.raises(ToolError) as excinfo:
        await server.call_tool("listar_radar", {})

    assert "radar" in str(excinfo.value).lower()
