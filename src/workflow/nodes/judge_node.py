from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
)
from pydantic import BaseModel

from src.agents.base.base_prompt import build_system_prompt
from src.agents.specialist.judge.judge_prompt import JUDGE_AGENT
from src.core.llm.llm_groq import llm_groq
from src.workflow.state import GraphState
from src.workflow.turn_tracking import append_turn_agent

JUDGE_PROMPT = build_system_prompt(JUDGE_AGENT, include_communication_standards=False)

MAX_JUDGE_RETRIES = 1

BLOCKED_RESPONSE = (
    "Não foi possível gerar uma resposta confiável para essa solicitação. "
    "Poderia reformular sua pergunta com mais detalhes?"
)


class VereditoJuiz(BaseModel):
    status: str
    justificativa: str


def judge_node(state: GraphState, config=None) -> dict:
    last_message = state["messages"][-1].content
    messages_with_context = [
        SystemMessage(content=JUDGE_PROMPT),
        HumanMessage(content=f"Resposta a ser auditada:\n\n{last_message}"),
    ]
    veredito = (
        llm_groq()
        .with_structured_output(VereditoJuiz)
        .invoke(messages_with_context, config=config)
    )
    status = veredito.status.strip().upper()

    retries = state.get("judge_retries", 0)

    if status == "APROVADO":
        return {
            "judge_status": "approved",
            "turn_agents": append_turn_agent(state, "judge_approved"),
        }

    if retries < MAX_JUDGE_RETRIES:
        return {
            "messages": [RemoveMessage(id=state["messages"][-1].id)],
            "judge_status": "retry",
            "judge_retries": retries + 1,
            "turn_agents": append_turn_agent(state, "judge_rejected"),
        }

    return {
        "messages": [
            RemoveMessage(id=state["messages"][-1].id),
            AIMessage(content=BLOCKED_RESPONSE),
        ],
        "judge_status": "blocked",
        "turn_agents": append_turn_agent(state, "judge_blocked"),
    }
