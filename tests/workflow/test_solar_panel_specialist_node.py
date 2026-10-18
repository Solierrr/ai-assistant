import asyncio
from unittest.mock import AsyncMock, Mock

from langchain_core.messages import AIMessage, HumanMessage

from src.tools.units import listar_minhas_unidades
from src.workflow.nodes import solar_panel_specialist_node


def test_solar_panel_specialist_node_returns_agent_response(monkeypatch):
    tool = Mock()
    tool.name = "recomendar_ofertas"
    monkeypatch.setattr(
        solar_panel_specialist_node,
        "get_mcp_tools_by_name",
        AsyncMock(return_value=[tool]),
    )

    agent = Mock()
    agent.ainvoke = AsyncMock(
        return_value={
            "messages": [AIMessage(content="A placa ideal depende do seu consumo...")]
        }
    )
    build_agent = Mock(return_value=agent)
    monkeypatch.setattr(solar_panel_specialist_node, "build_agent", build_agent)

    result = asyncio.run(
        solar_panel_specialist_node.solar_panel_specialist_node(
            {"messages": [HumanMessage(content="Qual placa solar eu devo escolher?")]}
        )
    )

    assert result["turn_agents"] == ["solar_panel_specialist"]
    assert result["messages"][0].content.startswith("A placa")
    build_agent.assert_called_once_with(
        solar_panel_specialist_node.SOLAR_PANEL_SPECIALIST_AGENT,
        tools=[tool, listar_minhas_unidades],
    )
    agent.ainvoke.assert_awaited_once_with(
        {"messages": [HumanMessage(content="Qual placa solar eu devo escolher?")]},
        config=None,
    )
