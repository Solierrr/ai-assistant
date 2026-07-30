from langchain_core.messages import AIMessage, SystemMessage

from src.agents.base.base_prompt import build_system_prompt
from src.agents.specialist.router.router_prompt import ROUTER_AGENT
from src.core.llm.llm_groq import llm_groq
from src.workflow.edges.routing_edges import available_specialist_routes
from src.workflow.nodes.context import messages_with_summary
from src.workflow.state import GraphState

ROUTER_PROMPT = build_system_prompt(ROUTER_AGENT)


def router_node(state: GraphState) -> dict:
    available_routes = sorted(available_specialist_routes(state))
    suggested_route = state.get("suggested_route", "")
    routing_context = (
        "Rotas disponiveis nesta solicitacao: "
        f"{', '.join(available_routes) or 'nenhuma'}.\n"
        "Escolha somente uma rota disponivel e responda no formato ROUTE=<rota>.\n"
        f"Rota sugerida pelo orquestrador: {suggested_route or 'nenhuma'}."
    )
    messages_with_context = [
        SystemMessage(content=ROUTER_PROMPT),
        SystemMessage(content=routing_context),
        *messages_with_summary(state),
    ]
    output = llm_groq().invoke(messages_with_context).content

    if "ROUTE=" in output:
        extracted_route = output.split("ROUTE=")[1].strip().splitlines()[0].lower()
        return {"route": extracted_route, "called_agents": ["router"]}

    return {
        "messages": [AIMessage(content=output)],
        "route": "end",
        "called_agents": ["router_direct_response"],
    }
