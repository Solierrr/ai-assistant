import logging

from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage
from pydantic import BaseModel

from src.agents.base.base_prompt import build_system_prompt
from src.core.guardrails.anonymize import anonymize_text
from src.core.guardrails.injection_patterns import (
    matches_injection_pattern,
    matches_internal_data_keyword,
)
from src.core.guardrails.prompt import _PROMPT_CLASSIFICADOR
from src.core.llm.llm_groq import llm_groq
from src.workflow.state import GraphState

logger = logging.getLogger(__name__)

INPUT_GUARDRAIL_PROMPT = build_system_prompt(
    _PROMPT_CLASSIFICADOR, include_communication_standards=False
)

BLOCKED_RESPONSE = (
    "Desculpe, não posso processar essa solicitação por políticas de segurança."
)


class ClassificacaoEntrada(BaseModel):
    categoria: str
    motivo: str


def _blocked_result(
    state: GraphState, category: str, pii_map: dict | None = None
) -> dict:
    return {
        "messages": [
            RemoveMessage(id=state["messages"][-1].id),
            AIMessage(content=BLOCKED_RESPONSE),
        ],
        "route": "end",
        "pii_map": pii_map or {},
        "turn_agents": [f"input_guardrail_blocked_{category.lower()}"],
    }


def input_guardrail_node(state: GraphState, config=None) -> dict:
    last_message = state["messages"][-1].content

    if matches_injection_pattern(last_message):
        return _blocked_result(state, "manipulacao_regex")
    if matches_internal_data_keyword(last_message):
        return _blocked_result(state, "dados_internos_regex")

    anonymized_text, pii_map = anonymize_text(last_message)
    formatted_prompt = INPUT_GUARDRAIL_PROMPT.format(mensagem=anonymized_text)

    try:
        classificacao = (
            llm_groq()
            .with_structured_output(ClassificacaoEntrada)
            .invoke([HumanMessage(content=formatted_prompt)], config=config)
        )
    except Exception as erro: 
        logger.warning("Falha ao avaliar input_guardrail: %s", erro)
        return _blocked_result(state, "falha_avaliacao_guardrail")

    category = classificacao.categoria.strip().upper()

    if category != "APROVADO":
        return _blocked_result(state, category, pii_map)

    return {
        "messages": [
            RemoveMessage(id=state["messages"][-1].id),
            HumanMessage(content=anonymized_text),
        ],
        "route": "proceed",
        "pii_map": pii_map,
        "turn_agents": ["input_guardrail_approved"],
    }
