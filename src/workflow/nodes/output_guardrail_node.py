from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage

from src.agents.base.base_prompt import build_system_prompt
from src.core.guardrails.anonymize import deanonymize_text
from src.core.guardrails.prompt import _PROMPT_COMPLIANCE
from src.core.llm.llm_groq import llm_groq
from src.workflow.state import GraphState
from src.workflow.turn_tracking import append_turn_agent, specialists_used

OUTPUT_GUARDRAIL_PROMPT = build_system_prompt(
    _PROMPT_COMPLIANCE, include_communication_standards=False
)


def output_guardrail_node(state: GraphState) -> dict:
    last_message_text = state["messages"][-1].content
    formatted_prompt = OUTPUT_GUARDRAIL_PROMPT.format(resposta=last_message_text)

    try:
        reviewed_response = (
            llm_groq().invoke([HumanMessage(content=formatted_prompt)]).content
        )
    except Exception:  # noqa: BLE001 — fail-closed: qualquer falha bloqueia
        # Falha fechado: se a revisão de compliance não puder rodar, não
        # deixa a resposta não revisada do agente vazar pro usuário.
        workflow_steps = append_turn_agent(state, "output_guardrail_failed_closed")
        return {
            "messages": [
                RemoveMessage(id=state["messages"][-1].id),
                AIMessage(
                    content=(
                        "Desculpe, não consegui concluir a revisão de "
                        "segurança da resposta. Tente novamente em instantes."
                    ),
                    additional_kwargs={
                        "specialists_used": specialists_used(workflow_steps),
                        "workflow_steps": workflow_steps,
                    },
                ),
            ],
            "turn_agents": workflow_steps,
        }

    final_response = reviewed_response
    if "RESPOSTA:" in reviewed_response.upper():
        final_response = reviewed_response.split("RESPOSTA:", 1)[-1].strip()

    final_text = deanonymize_text(final_response, state["pii_map"])
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
