import pytest

from src.workflow.edges.routing_edges import (
    decide_post_input_guardrail,
    decide_post_router,
)


def test_decide_post_input_guardrail_returns_end_for_end_route():
    assert decide_post_input_guardrail({"route": "end"}) == "end"


def test_decide_post_input_guardrail_returns_proceed_for_other_routes():
    assert decide_post_input_guardrail({"route": "solar_panel_specialist"}) == "proceed"


@pytest.mark.parametrize(
    "route",
    ["faq_reader", "professional_suggester", "agency_suggester", "solar_panel_specialist", "end"],
)
def test_decide_post_router_returns_the_selected_route(route):
    assert decide_post_router({"route": route}) == route


def test_decide_post_router_returns_orchestrator_directly():
    assert decide_post_router({"route": "orchestrator"}) == "orchestrator"


def test_decide_post_router_falls_back_to_orchestrator_when_route_was_already_consulted():
    assert (
        decide_post_router(
            {"route": "faq_reader", "turn_agents": ["faq_reader", "router"]}
        )
        == "orchestrator"
    )
