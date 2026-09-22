from unittest.mock import AsyncMock, Mock

from langchain_core.messages import AIMessage, HumanMessage

import src.workflow.nodes.solar_panel_specialist_node as node


async def test_solar_panel_specialist_node_returns_agent_response(monkeypatch):
    tool = Mock(name="listar_ofertas_de_placas")
    monkeypatch.setattr(node, "get_mcp_tool", AsyncMock(return_value=[tool]))
    invoke = AsyncMock(
        return_value={"messages": [AIMessage(content="A placa depende do consumo.")]}
    )
    monkeypatch.setattr(node, "invoke_agent_with_fallback", invoke)
    state = {"messages": [HumanMessage(content="Qual placa escolher?")]}

    result = await node.solar_panel_specialist_node(state)

    assert result["turn_agents"] == ["solar_panel_specialist"]
    invoke.assert_awaited_once_with(
        node.SOLAR_PANEL_SPECIALIST_AGENT,
        state["messages"],
        tools=[tool],
        config=None,
    )
