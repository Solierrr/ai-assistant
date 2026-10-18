import asyncio
from unittest.mock import AsyncMock, Mock

import src.infra.mcp.client as client


def _fake_tool(nome: str) -> Mock:
    tool = Mock()
    tool.name = nome
    return tool


def test_get_mcp_tools_carrega_uma_vez_so(monkeypatch):
    monkeypatch.setattr(client, "_tools_cache", None)
    tools_da_api = [_fake_tool("listar_ofertas_de_placas")]
    carregar_tools = AsyncMock(return_value=tools_da_api)
    monkeypatch.setattr(client, "_carregar_tools", carregar_tools)

    resultado_1 = asyncio.run(client.get_mcp_tools())
    resultado_2 = asyncio.run(client.get_mcp_tools())

    assert resultado_1 == tools_da_api
    assert resultado_2 == tools_da_api
    carregar_tools.assert_awaited_once()


def test_get_mcp_tool_filtra_pelo_nome_certo(monkeypatch):
    tools_da_api = [
        _fake_tool("listar_ofertas_de_placas"),
        _fake_tool("buscar_tecnicos_credenciados"),
    ]
    monkeypatch.setattr(client, "_tools_cache", tools_da_api)

    resultado = asyncio.run(client.get_mcp_tool("buscar_tecnicos_credenciados"))

    assert len(resultado) == 1
    assert resultado[0].name == "buscar_tecnicos_credenciados"


def test_get_mcp_tool_nome_inexistente_devolve_lista_vazia(monkeypatch):
    tools_da_api = [_fake_tool("listar_ofertas_de_placas")]
    monkeypatch.setattr(client, "_tools_cache", tools_da_api)

    resultado = asyncio.run(client.get_mcp_tool("tool_que_nao_existe"))

    assert resultado == []


def test_get_mcp_tools_by_name_devolve_so_as_pedidas(monkeypatch):
    tools_da_api = [
        _fake_tool("recomendar_ofertas"),
        _fake_tool("recomendar_profissionais"),
        _fake_tool("listar_profissoes"),
    ]
    monkeypatch.setattr(client, "_tools_cache", tools_da_api)

    resultado = asyncio.run(
        client.get_mcp_tools_by_name("recomendar_profissionais", "listar_profissoes")
    )

    assert [t.name for t in resultado] == [
        "recomendar_profissionais",
        "listar_profissoes",
    ]


def test_get_mcp_tools_by_name_avisa_quando_falta_uma(monkeypatch, caplog):
    monkeypatch.setattr(client, "_tools_cache", [_fake_tool("recomendar_ofertas")])

    with caplog.at_level("WARNING"):
        resultado = asyncio.run(
            client.get_mcp_tools_by_name("recomendar_ofertas", "ferramenta_antiga")
        )

    assert [t.name for t in resultado] == ["recomendar_ofertas"]
    assert "ferramenta_antiga" in caplog.text
