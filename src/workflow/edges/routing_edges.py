from src.workflow import config
from src.workflow.state import GraphState

SPECIALIST_ROUTES = frozenset(
    {
        "faq_reader",
        "professional_suggester",
        "agency_suggester",
        "solar_panel_specialist",
    }
)


def consulted_specialists(state: GraphState) -> set[str]:
    return set(state.get("called_agents", [])) & SPECIALIST_ROUTES


def available_specialist_routes(state: GraphState) -> set[str]:
    return SPECIALIST_ROUTES - consulted_specialists(state)


def decide_post_router(state: GraphState) -> str:
    route = state.get("route", "end")
    if route not in SPECIALIST_ROUTES:
        return "end"
    if route not in available_specialist_routes(state):
        return "end"
    return route


def decide_post_orchestrator(state: GraphState) -> str:
    if state.get("orchestrator_status") != "PRECISA_APOIO":
        return "output_guardrail"
    if len(consulted_specialists(state)) >= config.MAX_SPECIALISTS_PER_REQUEST:
        return "output_guardrail"
    if not available_specialist_routes(state):
        return "output_guardrail"
    return "router"


def decide_post_input_guardrail(state: GraphState) -> str:
    if state["route"] == "end":
        return "end"
    return "proceed"
