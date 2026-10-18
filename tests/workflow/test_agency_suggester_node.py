import asyncio
from unittest.mock import AsyncMock, Mock

from langchain_core.messages import AIMessage, HumanMessage

from src.tools.units import listar_minhas_unidades
from src.workflow.nodes import agency_suggester_node


def test_agency_suggester_node_returns_agent_response(monkeypatch):
    tool = Mock()
    tool.name = "recomendar_fornecedores"
    get_tools = AsyncMock(return_value=[tool])
    monkeypatch.setattr(agency_suggester_node, "get_mcp_tools_by_name", get_tools)

    agent = Mock()
    agent.ainvoke = AsyncMock(
        return_value={
            "messages": [
                AIMessage(content="Recomendo buscar um fornecedor regional...")
            ]
        }
    )
    build_agent = Mock(return_value=agent)
    monkeypatch.setattr(agency_suggester_node, "build_agent", build_agent)

    result = asyncio.run(
        agency_suggester_node.agency_suggester_node(
            {"messages": [HumanMessage(content="Preciso de um instalador em SP")]}
        )
    )

    assert result["turn_agents"] == ["agency_suggester"]
    assert result["messages"][0].content.startswith("Recomendo")
    get_tools.assert_awaited_once_with("recomendar_fornecedores")
    build_agent.assert_called_once_with(
        agency_suggester_node.AGENCY_SUGGESTER_AGENT,
        tools=[tool, listar_minhas_unidades],
    )
    agent.ainvoke.assert_awaited_once_with(
        {"messages": [HumanMessage(content="Preciso de um instalador em SP")]},
        config=None,
    )
