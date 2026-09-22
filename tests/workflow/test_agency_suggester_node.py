from unittest.mock import AsyncMock

from langchain_core.messages import AIMessage, HumanMessage

import src.workflow.nodes.agency_suggester_node as node


async def test_agency_suggester_node_returns_agent_response(monkeypatch):
    invoke = AsyncMock(
        return_value={"messages": [AIMessage(content="Fornecedor regional.")]}
    )
    monkeypatch.setattr(node, "invoke_agent_with_fallback", invoke)
    state = {"messages": [HumanMessage(content="Preciso de uma agência")]}

    result = await node.agency_suggester_node(state)

    assert result["turn_agents"] == ["agency_suggester"]
    assert result["messages"][0].content == "Fornecedor regional."
    invoke.assert_awaited_once_with(
        node.AGENCY_SUGGESTER_AGENT, state["messages"], config=None
    )
