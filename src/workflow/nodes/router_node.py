from langchain_core.messages import AIMessage, SystemMessage
from pydantic import BaseModel

from src.agents.base.base_prompt import build_system_prompt
from src.agents.specialist.router.router_prompt import ROUTER_AGENT
from src.core.llm.llm_groq import llm_groq
from src.workflow import config
from src.workflow.edges.routing_edges import (
    available_specialist_routes,
    consulted_specialists,
)
from src.workflow.nodes.context import messages_with_summary
from src.workflow.state import GraphState
from src.workflow.turn_tracking import append_turn_agent

ROUTER_PROMPT = build_system_prompt(ROUTER_AGENT)


class DecisaoRoteamento(BaseModel):
    rota: str | None  # None = responder direto, sem especialista
    resposta_direta: str | None = None


def router_node(state: GraphState, runnable_config=None) -> dict:
    consulted = consulted_specialists(state)
    available_routes = sorted(available_specialist_routes(state))
    limit_reached = len(consulted) >= config.MAX_SPECIALISTS_PER_REQUEST

    if consulted and (limit_reached or not available_routes):
        return {
            "route": "orchestrator",
            "turn_agents": append_turn_agent(state, "router"),
        }

    routing_context = (
        "Rotas disponiveis nesta solicitacao: "
        f"{', '.join(available_routes) or 'nenhuma'}.\n"
        "Se as respostas ja reunidas na conversa forem suficientes para "
        "responder ao usuario, preencha rota=orchestrator.\n"
        "Caso contrario, preencha rota com uma das rotas disponiveis acima.\n"
        "Se nenhuma rota for necessaria e voce puder responder diretamente, "
        "deixe rota vazia (None) e preencha resposta_direta."
    )
    messages_with_context = [
        SystemMessage(content=ROUTER_PROMPT),
        SystemMessage(content=routing_context),
        *messages_with_summary(state),
    ]
    decisao = (
        llm_groq()
        .with_structured_output(DecisaoRoteamento)
        .invoke(messages_with_context, config=runnable_config)
    )

    if decisao.rota:
        return {
            "route": decisao.rota.strip().lower(),
            "turn_agents": append_turn_agent(state, "router"),
        }

    return {
        "messages": [AIMessage(content=decisao.resposta_direta or "")],
        "route": "end",
        "turn_agents": append_turn_agent(state, "router_direct_response"),
    }
