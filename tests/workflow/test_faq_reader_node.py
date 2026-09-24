from unittest.mock import Mock

from langchain_core.messages import AIMessage, HumanMessage

import src.workflow.nodes.faq_reader_node as faq_reader_node


def test_faq_reader_node_returns_agent_response(monkeypatch):
    agent = Mock()
    agent.invoke.return_value = {
        "messages": [AIMessage(content="A garantia do painel varia conforme o fabricante.")]
    }
    build_agent = Mock(return_value=agent)
    monkeypatch.setattr(faq_reader_node, "build_agent", build_agent)

    result = faq_reader_node.faq_reader_node(
        {"messages": [HumanMessage(content="Qual é a garantia do painel?")]}
    )

    assert result["turn_agents"] == ["faq_reader"]
    assert result["messages"][0].content.startswith("A garantia")
    build_agent.assert_called_once_with(
        faq_reader_node.FAQ_READER_AGENT, tools=[faq_reader_node.faq_retriever]
    )
    agent.invoke.assert_called_once_with(
        {"messages": [HumanMessage(content="Qual é a garantia do painel?")]},
        config=None,
    )
