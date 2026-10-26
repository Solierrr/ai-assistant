"""Resultado do turno (`outcome` e `reason`) lido do estado final do grafo, para o
front mostrar a mensagem certa sem tratar recusa ou falha interna como erro HTTP."""

from enum import StrEnum

from src.workflow.nodes.operational_delegate_node import _INDISPONIVEL
from src.workflow.nodes.output_guardrail_node import FALLBACK_RESPONSE


class TurnOutcome(StrEnum):
    ANSWERED = "ANSWERED"
    REFUSED = "REFUSED"
    DEGRADED = "DEGRADED"
    TOOL_FAILED = "TOOL_FAILED"


class Reason(StrEnum):
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    MANIPULATION_ATTEMPT = "MANIPULATION_ATTEMPT"
    INTERNAL_DATA_REQUEST = "INTERNAL_DATA_REQUEST"
    FALSE_INFORMATION = "FALSE_INFORMATION"
    GUARDRAIL_REFUSED = "GUARDRAIL_REFUSED"
    GUARDRAIL_UNAVAILABLE = "GUARDRAIL_UNAVAILABLE"
    ANSWER_REJECTED = "ANSWER_REJECTED"
    OPERATIONAL_AGENT_UNAVAILABLE = "OPERATIONAL_AGENT_UNAVAILABLE"


_BLOCKED_PREFIX = "input_guardrail_blocked_"

_REFUSAL_REASONS = {
    "fora_escopo": Reason.OUT_OF_SCOPE,
    "redirecionar": Reason.OUT_OF_SCOPE,
    "manipulacao": Reason.MANIPULATION_ATTEMPT,
    "manipulacao_regex": Reason.MANIPULATION_ATTEMPT,
    "dados_internos": Reason.INTERNAL_DATA_REQUEST,
    "dados_internos_regex": Reason.INTERNAL_DATA_REQUEST,
    "informacao_falsa": Reason.FALSE_INFORMATION,
}


def turn_outcome(final_state: dict) -> tuple[TurnOutcome, Reason | None]:
    steps = final_state.get("turn_agents", [])
    content = final_state["messages"][-1].content

    for step in steps:
        if step.startswith(_BLOCKED_PREFIX):
            category = step.removeprefix(_BLOCKED_PREFIX)
            if category == "falha_avaliacao_guardrail":
                return TurnOutcome.DEGRADED, Reason.GUARDRAIL_UNAVAILABLE
            return TurnOutcome.REFUSED, _REFUSAL_REASONS.get(
                category, Reason.GUARDRAIL_REFUSED
            )
    if content == FALLBACK_RESPONSE:
        return TurnOutcome.DEGRADED, Reason.GUARDRAIL_UNAVAILABLE
    if "judge_blocked" in steps:
        return TurnOutcome.REFUSED, Reason.ANSWER_REJECTED
    if content == _INDISPONIVEL:
        return TurnOutcome.TOOL_FAILED, Reason.OPERATIONAL_AGENT_UNAVAILABLE
    return TurnOutcome.ANSWERED, None
