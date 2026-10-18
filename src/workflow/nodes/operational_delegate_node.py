import logging

from ai_lib.a2a import DelegationError, delegate
from langchain_core.messages import AIMessage, HumanMessage

from src.core.config.settings import settings
from src.core.security.request_context import current_persona, current_user_token
from src.workflow.state import GraphState
from src.workflow.turn_tracking import append_turn_agent

logger = logging.getLogger(__name__)

_INDISPONIVEL = (
    "Não consegui falar com o agente que executa ações na plataforma agora. "
    "Tente novamente em instantes."
)
_SEM_TOKEN = "Para executar ações na plataforma é preciso estar autenticado."


def _message(text: str, turn_agents: list[str]) -> AIMessage:
    return AIMessage(
        content=text,
        additional_kwargs={
            "specialists_used": ["operational_delegate"],
            "workflow_steps": turn_agents,
        },
    )


def _last_user_text(state: GraphState) -> str:
    for message in reversed(state["messages"]):
        if isinstance(message, HumanMessage):
            return str(message.content)
    return ""


async def operational_delegate_node(state: GraphState, config=None) -> dict:
    """Delega ao ai-operational (A2A) um pedido de ação no SaaS.

    A resposta do agente remoto segue direto para o usuário, sem passar pelo
    orquestrador, pelo juiz nem pelo guardrail de saída (o agente remoto já aplicou os
    dele): uma proposta tem de chegar exatamente como foi escrita. Quando o
    agente remoto espera a decisão (aceitar, recusar ou questionar), o estado guarda
    `awaiting_decision` e a próxima mensagem volta para ele."""
    turn_agents = append_turn_agent(state, "operational_delegate")
    token = current_user_token.get()
    if not token:
        return {
            "messages": [_message(_SEM_TOKEN, turn_agents)],
            "turn_agents": turn_agents,
            "awaiting_decision": False,
        }

    thread_id = ((config or {}).get("configurable") or {}).get("thread_id")
    try:
        resultado = await delegate(
            settings.A2A_OPERATIONAL_URL,
            _last_user_text(state),
            token=token,
            persona=current_persona.get(),
            context_id=thread_id,
        )
    except DelegationError:
        logger.exception("Falha ao delegar ao ai-operational")
        return {
            "messages": [_message(_INDISPONIVEL, turn_agents)],
            "turn_agents": turn_agents,
            "awaiting_decision": False,
        }

    if (
        resultado.outcome in ("failed", "rejected", "canceled", "unknown")
        or not resultado.text
    ):
        return {
            "messages": [_message(_INDISPONIVEL, turn_agents)],
            "turn_agents": turn_agents,
            "awaiting_decision": False,
        }

    return {
        "messages": [_message(resultado.text, turn_agents)],
        "turn_agents": turn_agents,
        "awaiting_decision": resultado.outcome == "input_required",
    }
