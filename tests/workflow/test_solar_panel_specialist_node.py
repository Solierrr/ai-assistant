from unittest.mock import Mock

from langchain_core.messages import AIMessage, HumanMessage

import src.workflow.nodes.solar_panel_specialist_node as solar_panel_specialist_node


def test_solar_panel_specialist_node_returns_agent_response(monkeypatch):
    agent = Mock()
    agent.invoke.return_value = {
        "messages": [AIMessage(content="A placa ideal depende do seu consumo...")]
    }
    monkeypatch.setattr(
        solar_panel_specialist_node, "build_agent", Mock(return_value=agent)
    )

    result = solar_panel_specialist_node.solar_panel_specialist_node(
        {"messages": [HumanMessage(content="Qual placa solar eu devo escolher?")]}
    )

    assert result["turn_agents"] == ["solar_panel_specialist"]
    assert result["messages"][0].content.startswith("A placa")
    agent.invoke.assert_called_once_with(
        {"messages": [HumanMessage(content="Qual placa solar eu devo escolher?")]}
    )
