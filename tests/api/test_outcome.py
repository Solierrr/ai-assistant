import pytest
from langchain_core.messages import AIMessage

from src.api.outcome import TurnOutcome, turn_outcome
from src.workflow.nodes.input_guardrail_node import BLOCKED_RESPONSE
from src.workflow.nodes.judge_node import BLOCKED_RESPONSE as JUDGE_BLOCKED
from src.workflow.nodes.operational_delegate_node import _INDISPONIVEL
from src.workflow.nodes.output_guardrail_node import FALLBACK_RESPONSE


def _state(content, steps):
    return {"messages": [AIMessage(content=content)], "turn_agents": steps}


@pytest.mark.parametrize(
    ("content", "steps", "expected"),
    [
        (
            "Recomendo um instalador.",
            ["input_guardrail_approved", "router", "orchestrator", "output_guardrail"],
            (TurnOutcome.ANSWERED, None),
        ),
        (
            BLOCKED_RESPONSE,
            ["input_guardrail_blocked_manipulacao"],
            (TurnOutcome.REFUSED, "MANIPULATION_ATTEMPT"),
        ),
        (
            BLOCKED_RESPONSE,
            ["input_guardrail_blocked_fora_escopo"],
            (TurnOutcome.REFUSED, "OUT_OF_SCOPE"),
        ),
        (
            BLOCKED_RESPONSE,
            ["input_guardrail_blocked_dados_internos_regex"],
            (TurnOutcome.REFUSED, "INTERNAL_DATA_REQUEST"),
        ),
        (
            BLOCKED_RESPONSE,
            ["input_guardrail_blocked_categoria_nova"],
            (TurnOutcome.REFUSED, "GUARDRAIL_REFUSED"),
        ),
        (
            BLOCKED_RESPONSE,
            ["input_guardrail_blocked_falha_avaliacao_guardrail"],
            (TurnOutcome.DEGRADED, "GUARDRAIL_UNAVAILABLE"),
        ),
        (
            JUDGE_BLOCKED,
            ["orchestrator", "judge_rejected", "judge_blocked", "output_guardrail"],
            (TurnOutcome.REFUSED, "ANSWER_REJECTED"),
        ),
        (
            FALLBACK_RESPONSE,
            ["orchestrator", "judge_approved", "output_guardrail"],
            (TurnOutcome.DEGRADED, "GUARDRAIL_UNAVAILABLE"),
        ),
        (
            _INDISPONIVEL,
            ["router", "operational_delegate"],
            (TurnOutcome.TOOL_FAILED, "OPERATIONAL_AGENT_UNAVAILABLE"),
        ),
    ],
)
def test_turn_outcome(content, steps, expected):
    assert turn_outcome(_state(content, steps)) == expected


def test_turn_outcome_without_steps_is_answered():
    assert turn_outcome({"messages": [AIMessage(content="Oi")]}) == (
        TurnOutcome.ANSWERED,
        None,
    )
