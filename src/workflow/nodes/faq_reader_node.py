from langchain_core.messages import AIMessage

from src.agents.base.base_agent import invoke_agent_with_fallback
from src.agents.specialist.faq_reader.faq_reader_prompt import FAQ_READER_AGENT
from src.agents.specialist.faq_reader.tools.faq_retriever import faq_retriever
from src.workflow.nodes.context import messages_with_summary
from src.workflow.state import GraphState
from src.workflow.turn_tracking import append_turn_agent


async def faq_reader_node(state: GraphState, config=None) -> dict:
    result = await invoke_agent_with_fallback(
        FAQ_READER_AGENT,
        messages_with_summary(state),
        tools=[faq_retriever],
        config=config,
    )
    last_message = result["messages"][-1]

    return {
        "messages": [AIMessage(content=last_message.content)],
        "turn_agents": append_turn_agent(state, "faq_reader"),
    }
