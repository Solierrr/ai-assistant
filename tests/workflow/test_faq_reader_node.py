from unittest.mock import AsyncMock

from langchain_core.messages import AIMessage, HumanMessage

import src.workflow.nodes.faq_reader_node as node


async def test_faq_reader_node_returns_agent_response(monkeypatch):
    invoke = AsyncMock(
        return_value={"messages": [AIMessage(content="A garantia varia.")]}
    )
    monkeypatch.setattr(node, "invoke_agent_with_fallback", invoke)
    state = {"messages": [HumanMessage(content="Qual é a garantia?")]}

    result = await node.faq_reader_node(state)

    assert result["turn_agents"] == ["faq_reader"]
    assert result["messages"][0].content == "A garantia varia."
    invoke.assert_awaited_once_with(
        node.FAQ_READER_AGENT,
        state["messages"],
        tools=[node.faq_retriever],
        config=None,
    )
