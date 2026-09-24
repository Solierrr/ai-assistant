from unittest.mock import Mock

from langchain_core.messages import AIMessage, HumanMessage

import src.workflow.nodes.agency_suggester_node as agency_suggester_node


def test_agency_suggester_node_returns_agent_response(monkeypatch):
    agent = Mock()
    agent.invoke.return_value = {
        "messages": [AIMessage(content="Recomendo buscar um fornecedor regional...")]
    }
    monkeypatch.setattr(
        agency_suggester_node, "build_agent", Mock(return_value=agent)
    )

    result = agency_suggester_node.agency_suggester_node(
        {"messages": [HumanMessage(content="Preciso de um instalador em SP")]}
    )

    assert result["turn_agents"] == ["agency_suggester"]
    assert result["messages"][0].content.startswith("Recomendo")
    agent.invoke.assert_called_once_with(
        {"messages": [HumanMessage(content="Preciso de um instalador em SP")]},
        config=None,
    )
