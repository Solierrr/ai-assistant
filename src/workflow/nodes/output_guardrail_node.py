from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage

from src.agents.base.base_prompt import build_system_prompt
from src.core.guardrails.anonymize import deanonymize_text
from src.core.guardrails.prompt import _PROMPT_COMPLIANCE
from src.core.llm.llm_groq import llm_groq
from src.workflow.state import GraphState

OUTPUT_GUARDRAIL_PROMPT = build_system_prompt(
    _PROMPT_COMPLIANCE, include_communication_standards=False
)


def output_guardrail_node(state: GraphState) -> dict:
    last_message_text = state["messages"][-1].content
    formatted_prompt = OUTPUT_GUARDRAIL_PROMPT.format(resposta=last_message_text)
    reviewed_response = (
        llm_groq().invoke([HumanMessage(content=formatted_prompt)]).content
    )

    final_response = reviewed_response
    if "RESPOSTA:" in reviewed_response.upper():
        final_response = reviewed_response.split("RESPOSTA:", 1)[-1].strip()

    final_text = deanonymize_text(final_response, state["pii_map"])

    return {
        "messages": [
            RemoveMessage(id=state["messages"][-1].id),
            AIMessage(content=final_text),
        ],
        "called_agents": ["output_guardrail"],
    }
