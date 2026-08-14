from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage

from src.agents.base.base_prompt import build_system_prompt
from src.core.guardrails.anonymize import anonymize_text
from src.core.guardrails.injection_filter import pre_filter_category
from src.core.guardrails.injection_filter import pre_filter_category
from src.core.guardrails.prompt import _PROMPT_CLASSIFICADOR
from src.core.llm.llm_groq import llm_groq
from src.workflow.state import GraphState

INPUT_GUARDRAIL_PROMPT = build_system_prompt(
    _PROMPT_CLASSIFICADOR, include_communication_standards=False
)


def input_guardrail_node(state: GraphState) -> dict:
    last_message = state["messages"][-1].content
    anonymized_text, pii_map = anonymize_text(last_message)

    category = pre_filter_category(anonymized_text)
    if category is None:
        category = _classify_via_llm(anonymized_text)

    if category != "APROVADO":
        return {
            "messages": [
                RemoveMessage(id=state["messages"][-1].id),
                AIMessage(
                    content="Desculpe, não posso processar essa solicitação por políticas de segurança."
                ),
            ],
            "route": "end",
            "pii_map": pii_map,
            "turn_agents": [f"input_guardrail_blocked_{category.lower()}"],
        }

    return {
        "messages": [
            RemoveMessage(id=state["messages"][-1].id),
            HumanMessage(content=anonymized_text),
        ],
        "route": "proceed",
        "pii_map": pii_map,
        "turn_agents": ["input_guardrail_approved"],
    }
