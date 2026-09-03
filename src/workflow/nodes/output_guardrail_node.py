import logging

from groq import GroqError
from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage
from pydantic import BaseModel, ValidationError

from src.agents.base.base_prompt import build_system_prompt
from src.core.guardrails.anonymize import deanonymize_text
from src.core.guardrails.prompt import _PROMPT_COMPLIANCE
from src.core.llm.llm_groq import llm_groq
from src.workflow.state import GraphState
from src.workflow.turn_tracking import append_turn_agent, specialists_used

logger = logging.getLogger(__name__)

OUTPUT_GUARDRAIL_PROMPT = build_system_prompt(
    _PROMPT_COMPLIANCE, include_communication_standards=False
)

FALLBACK_RESPONSE = "Não foi possível processar sua solicitação no momento. Tente novamente em instantes."


class RevisaoCompliance(BaseModel):
    resposta_revisada: str
    foi_corrigida: bool


def output_guardrail_node(state: GraphState, config=None) -> dict:
    last_message_text = state["messages"][-1].content
    formatted_prompt = OUTPUT_GUARDRAIL_PROMPT.format(resposta=last_message_text)

    try:
        revisao = (
            llm_groq()
            .with_structured_output(RevisaoCompliance)
            .invoke([HumanMessage(content=formatted_prompt)], config=config)
        )
        final_text = deanonymize_text(revisao.resposta_revisada, state["pii_map"])
    except (GroqError, ValidationError) as erro:
        # fail-closed: se o guardrail nao conseguiu revisar, nao deixa a
        # resposta nao revisada sair - troca por uma mensagem generica
        logger.warning("Falha ao avaliar output_guardrail: %s", erro)
        final_text = FALLBACK_RESPONSE

    workflow_steps = append_turn_agent(state, "output_guardrail")

    return {
        "messages": [
            RemoveMessage(id=state["messages"][-1].id),
            AIMessage(
                content=final_text,
                additional_kwargs={
                    "specialists_used": specialists_used(workflow_steps),
                    "workflow_steps": workflow_steps,
                },
            ),
        ],
        "turn_agents": workflow_steps,
    }
