from unittest.mock import Mock

from langchain_core.messages import AIMessage, HumanMessage

import src.workflow.nodes.professional_suggester_node as professional_suggester_node


def test_professional_suggester_node_returns_agent_response(monkeypatch):
    agent = Mock()
    agent.invoke.return_value = {
        "messages": [AIMessage(content="Procure um profissional certificado...")]
    }
    monkeypatch.setattr(
        professional_suggester_node, "build_agent", Mock(return_value=agent)
    )

    result = professional_suggester_node.professional_suggester_node(
        {"messages": [HumanMessage(content="Preciso de um instalador em SP")]}
    )

    assert result["called_agents"] == ["professional_suggester"]
    assert result["messages"][0].content.startswith("Procure")
    agent.invoke.assert_called_once_with(
        {"messages": [HumanMessage(content="Preciso de um instalador em SP")]}
    )
