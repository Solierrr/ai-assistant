from langchain_core.messages import AIMessage

from src.agents.base.base_agent import build_agent
from src.agents.specialist.agency_suggester.agency_suggester_prompt import (
    AGENCY_SUGGESTER_AGENT,
)
from src.workflow.nodes.context import messages_with_summary
from src.workflow.state import GraphState
from src.workflow.turn_tracking import append_turn_agent


def agency_suggester_node(state: GraphState, config=None) -> dict:
    agent = build_agent(AGENCY_SUGGESTER_AGENT)
    result = agent.invoke({"messages": messages_with_summary(state)}, config=config)
    last_message = result["messages"][-1]

    return {
        "messages": [AIMessage(content=last_message.content)],
        "turn_agents": append_turn_agent(state, "agency_suggester"),
    }
