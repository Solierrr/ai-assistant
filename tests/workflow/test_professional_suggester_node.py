from unittest.mock import AsyncMock, Mock

from langchain_core.messages import AIMessage, HumanMessage

import src.workflow.nodes.professional_suggester_node as node


async def test_professional_suggester_node_returns_agent_response(monkeypatch):
    tool = Mock(name="buscar_tecnicos_credenciados")
    monkeypatch.setattr(node, "get_mcp_tool", AsyncMock(return_value=[tool]))
    invoke = AsyncMock(
        return_value={"messages": [AIMessage(content="Profissional certificado.")]}
    )
    monkeypatch.setattr(node, "invoke_agent_with_fallback", invoke)
    state = {"messages": [HumanMessage(content="Preciso de instalador")]}

    result = await node.professional_suggester_node(state)

    assert result["turn_agents"] == ["professional_suggester"]
    invoke.assert_awaited_once_with(
        node.PROFESSIONAL_SUGGESTER_AGENT,
        state["messages"],
        tools=[tool],
        config=None,
    )
