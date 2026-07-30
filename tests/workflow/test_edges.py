import pytest

from src.workflow.edges.routing_edges import (
    decide_post_input_guardrail,
    decide_post_orchestrator,
    decide_post_router,
)


def test_decide_post_input_guardrail_returns_end_for_end_route():
    assert decide_post_input_guardrail({"route": "end"}) == "end"


def test_decide_post_input_guardrail_returns_proceed_for_other_routes():
    assert decide_post_input_guardrail({"route": "solar_panel_specialist"}) == "proceed"


@pytest.mark.parametrize(
    "route",
    [
        "faq_reader",
        "professional_suggester",
        "agency_suggester",
        "solar_panel_specialist",
        "end",
    ],
)
def test_decide_post_router_returns_the_selected_route(route):
    assert decide_post_router({"route": route}) == route


def test_decide_post_router_ends_when_route_was_already_consulted():
    assert (
        decide_post_router(
            {
                "route": "faq_reader",
                "called_agents": ["faq_reader", "orchestrator"],
            }
        )
        == "end"
    )


def test_decide_post_orchestrator_sends_sufficient_response_to_output_guardrail():
    assert (
        decide_post_orchestrator(
            {
                "orchestrator_status": "SUFICIENTE",
                "called_agents": ["solar_panel_specialist", "orchestrator"],
            }
        )
        == "output_guardrail"
    )


def test_decide_post_orchestrator_returns_to_router_when_support_is_available():
    assert (
        decide_post_orchestrator(
            {
                "orchestrator_status": "PRECISA_APOIO",
                "called_agents": ["solar_panel_specialist", "orchestrator"],
            }
        )
        == "router"
    )


def test_decide_post_orchestrator_forces_output_when_specialist_limit_is_reached(
    monkeypatch,
):
    from src.workflow import config

    monkeypatch.setattr(config, "MAX_SPECIALISTS_PER_REQUEST", 2)

    assert (
        decide_post_orchestrator(
            {
                "orchestrator_status": "PRECISA_APOIO",
                "called_agents": ["faq_reader", "solar_panel_specialist", "orchestrator"],
            }
        )
        == "output_guardrail"
    )
