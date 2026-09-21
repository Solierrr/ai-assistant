from langchain_core.messages import AIMessage

from src.agents.base.base_agent import build_agent
from src.agents.specialist.solar_calculator.solar_calculator_prompt import (
    SOLAR_CALCULATOR_AGENT,
)
from src.infra.billscanner.client import get_billscanner_tools
from src.workflow.nodes.context import messages_with_summary
from src.workflow.state import GraphState
from src.workflow.turn_tracking import append_turn_agent


async def solar_calculator_node(state: GraphState, config=None) -> dict:
    tools = get_billscanner_tools()
    agent = build_agent(SOLAR_CALCULATOR_AGENT, tools=tools)
    result = await agent.ainvoke(
        {"messages": messages_with_summary(state)}, config=config
    )
    last_message = result["messages"][-1]

    return {
        "messages": [AIMessage(content=last_message.content)],
        "turn_agents": append_turn_agent(state, "solar_calculator"),
    }
