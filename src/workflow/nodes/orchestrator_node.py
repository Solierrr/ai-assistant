from langchain_core.messages import AIMessage, SystemMessage

from src.agents.base.base_prompt import build_system_prompt
from src.agents.specialist.orchestrator.orchestrator_prompt import ORCHESTRATOR_AGENT
from src.core.llm.llm_gemini import llm_gemini
from src.core.llm.llm_groq import llm_groq
from src.workflow.state import GraphState

ORCHESTRATOR_PROMPT = build_system_prompt(ORCHESTRATOR_AGENT)


def orchestrator_node(state: GraphState) -> dict:
    messages_with_context = [SystemMessage(content=ORCHESTRATOR_PROMPT)] + state[
        "messages"
    ]
    output = (
        llm_gemini().with_fallbacks([llm_groq()]).invoke(messages_with_context).content
    )

    return {
        "messages": [AIMessage(content=output)],
        "called_agents": ["orchestrator"],
    }
