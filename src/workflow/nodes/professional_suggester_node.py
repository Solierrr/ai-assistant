from langchain_core.messages import AIMessage

from src.agents.base.base_agent import build_agent
from src.agents.specialist.professional_suggester.professional_suggester_prompt import (
    PROFESSIONAL_SUGGESTER_AGENT,
)
from src.workflow.state import GraphState


def professional_suggester_node(state: GraphState) -> dict:
    agent = build_agent(PROFESSIONAL_SUGGESTER_AGENT)
    result = agent.invoke({"messages": state["messages"]})
    last_message = result["messages"][-1]

    return {
        "messages": [AIMessage(content=last_message.content)],
        "called_agents": ["professional_suggester"],
    }
