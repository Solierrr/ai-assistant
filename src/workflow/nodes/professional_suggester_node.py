from langchain_core.messages import AIMessage

from src.agents.base.base_agent import build_agent
from src.agents.specialist.professional_suggester.professional_suggester_prompt import (
    PROFESSIONAL_SUGGESTER_AGENT,
)
from src.workflow.nodes.context import messages_ending_with_user
from src.workflow.state import GraphState
from src.workflow.turn_tracking import append_turn_agent


def professional_suggester_node(state: GraphState) -> dict:
    agent = build_agent(PROFESSIONAL_SUGGESTER_AGENT)
    result = agent.invoke({"messages": messages_ending_with_user(state)})
    last_message = result["messages"][-1]

    return {
        "messages": [AIMessage(content=last_message.content)],
        "turn_agents": append_turn_agent(state, "professional_suggester"),
    }
