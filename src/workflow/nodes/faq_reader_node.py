from langchain_core.messages import AIMessage

from src.agents.base.base_agent import build_agent
from src.agents.specialist.faq_reader.faq_reader_prompt import FAQ_READER_AGENT
from src.workflow.state import GraphState


def faq_reader_node(state: GraphState) -> dict:
    agent = build_agent(FAQ_READER_AGENT, tools=[])
    result = agent.invoke({"messages": state["messages"]})
    last_message = result["messages"][-1]

    return {
        "messages": [AIMessage(content=last_message.content)],
        "called_agents": ["faq_reader"],
    }
