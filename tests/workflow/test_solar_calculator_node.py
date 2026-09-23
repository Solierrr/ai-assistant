import asyncio
from unittest.mock import AsyncMock, Mock

from langchain_core.messages import AIMessage, HumanMessage

from src.workflow.nodes import solar_calculator_node


def test_solar_calculator_node_returns_agent_response(monkeypatch):
    tool = Mock()
    tool.name = "calcular_sistema_solar"
    monkeypatch.setattr(
        solar_calculator_node,
        "get_solar_calculator_tools",
        Mock(return_value=[tool]),
    )

    agent = Mock()
    agent.ainvoke = AsyncMock(
        return_value={
            "messages": [
                AIMessage(content="A estimativa preliminar indica 8 painéis.")
            ]
        }
    )
    build_agent = Mock(return_value=agent)
    monkeypatch.setattr(solar_calculator_node, "build_agent", build_agent)

    result = asyncio.run(
        solar_calculator_node.solar_calculator_node(
            {"messages": [HumanMessage(content="Calcule meu sistema solar.")]}
        )
    )

    assert result["turn_agents"] == ["solar_calculator"]
    assert result["messages"][0].content.startswith("A estimativa")
    build_agent.assert_called_once_with(
        solar_calculator_node.SOLAR_CALCULATOR_AGENT,
        tools=[tool],
    )
    agent.ainvoke.assert_awaited_once_with(
        {"messages": [HumanMessage(content="Calcule meu sistema solar.")]},
        config=None,
    )
