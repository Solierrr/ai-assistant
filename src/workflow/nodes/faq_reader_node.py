from langchain_core.messages import AIMessage

from src.agents.base.base_agent import build_agent
from src.agents.specialist.faq_reader.faq_reader_prompt import FAQ_READER_AGENT
from src.agents.specialist.faq_reader.tools.faq_retriever import faq_retriever
from src.workflow.nodes.context import messages_ending_with_user
from src.workflow.state import GraphState
from src.workflow.turn_tracking import append_turn_agent


def faq_reader_node(state: GraphState) -> dict:
    agent = build_agent(FAQ_READER_AGENT, tools=[faq_retriever])
    result = agent.invoke({"messages": messages_ending_with_user(state)})
    last_message = result["messages"][-1]

    return {
        "messages": [AIMessage(content=last_message.content)],
        "turn_agents": append_turn_agent(state, "faq_reader"),
    }
