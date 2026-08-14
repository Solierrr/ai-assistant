from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage

from src.agents.base.base_prompt import build_system_prompt
from src.core.guardrails.anonymize import anonymize_text
from src.core.guardrails.injection_filter import pre_filter_category
from src.core.guardrails.prompt import _PROMPT_CLASSIFICADOR
from src.core.llm.llm_groq import llm_groq
from src.workflow.state import GraphState

INPUT_GUARDRAIL_PROMPT = build_system_prompt(
    _PROMPT_CLASSIFICADOR, include_communication_standards=False
)


def _classify_via_llm(anonymized_text: str) -> str:
    """Classifica a mensagem via LLM. Se a chamada falhar (timeout, erro de
    API etc.), falha fechado: bloqueia por padrão em vez de deixar a exceção
    subir e expor o request sem checagem nenhuma."""
    formatted_prompt = INPUT_GUARDRAIL_PROMPT.format(mensagem=anonymized_text)
    try:
        response = llm_groq().invoke([HumanMessage(content=formatted_prompt)]).content
    except Exception:  # noqa: BLE001 — fail-closed: qualquer falha bloqueia
        return "ERRO_LLM"

    for line in response.splitlines():
        if line.upper().startswith("CATEGORIA:"):
            return line.split(":", 1)[1].strip().upper()

    return "INDEFINIDO"


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
