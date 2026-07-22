from src.workflow.edges.routing_edges import (
    decide_post_input_guardrail,
    decide_post_router,
)


def test_decide_post_input_guardrail_returns_end_for_end_route():
    assert decide_post_input_guardrail({"route": "end"}) == "end"


def test_decide_post_input_guardrail_returns_proceed_for_other_routes():
    assert decide_post_input_guardrail({"route": "solar_panel_specialist"}) == "proceed"


def test_decide_post_router_returns_end_for_end_route():
    assert decide_post_router({"route": "end"}) == "end"


def test_decide_post_router_returns_proceed_for_other_routes():
    assert decide_post_router({"route": "orchestrator"}) == "proceed"
