from langchain_core.messages import AIMessage

from src.agents.base.base_agent import build_agent
from src.agents.specialist.solar_panel_specialist.solar_panel_specialist_prompt import (
    SOLAR_PANEL_SPECIALIST_AGENT,
)
from src.workflow.nodes.context import messages_with_summary
from src.workflow.state import GraphState


def solar_panel_specialist_node(state: GraphState) -> dict:
    agent = build_agent(SOLAR_PANEL_SPECIALIST_AGENT)
    result = agent.invoke({"messages": messages_with_summary(state)})
    last_message = result["messages"][-1]

    return {
        "messages": [AIMessage(content=last_message.content)],
        "called_agents": ["solar_panel_specialist"],
    }
