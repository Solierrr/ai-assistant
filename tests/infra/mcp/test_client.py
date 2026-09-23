from unittest.mock import AsyncMock, Mock

from src.infra.mcp import client


def _tool(name: str) -> Mock:
    tool = Mock()
    tool.name = name
    return tool


async def test_get_mcp_tools_uses_cache(monkeypatch):
    tools = [_tool("listar_ofertas_de_placas")]
    load_tools = AsyncMock(return_value=tools)
    monkeypatch.setattr(client, "_tools_cache", None)
    monkeypatch.setattr(client, "_load_tools", load_tools)

    assert await client.get_mcp_tools() == tools
    assert await client.get_mcp_tools() == tools
    load_tools.assert_awaited_once()


async def test_get_mcp_tool_filters_by_name(monkeypatch):
    expected = _tool("buscar_tecnicos_credenciados")
    monkeypatch.setattr(
        client,
        "_tools_cache",
        [_tool("listar_ofertas_de_placas"), expected],
    )

    assert await client.get_mcp_tool("buscar_tecnicos_credenciados") == [expected]
