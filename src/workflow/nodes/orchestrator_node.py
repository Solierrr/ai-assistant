from langchain_core.messages import AIMessage, SystemMessage

from src.agents.base.base_prompt import build_system_prompt
from src.agents.specialist.orchestrator.orchestrator_prompt import ORCHESTRATOR_AGENT
from src.core.llm.llm_gemini import llm_gemini
from src.core.llm.llm_groq import llm_groq
from src.workflow.nodes.context import messages_with_summary
from src.workflow.state import GraphState

ORCHESTRATOR_PROMPT = build_system_prompt(ORCHESTRATOR_AGENT)


def orchestrator_node(state: GraphState) -> dict:
    messages_with_context = [
        SystemMessage(content=ORCHESTRATOR_PROMPT),
        *messages_with_summary(state),
    ]
    output = (
        llm_gemini().with_fallbacks([llm_groq()]).invoke(messages_with_context).content
    )

    status = "SUFICIENTE"
    suggested_route = ""
    response = output.strip()

    for line in output.splitlines():
        key, separator, value = line.partition(":")
        if not separator:
            continue
        if key.strip().upper() == "STATUS" and value.strip().upper() in {
            "SUFICIENTE",
            "PRECISA_APOIO",
        }:
            status = value.strip().upper()
        if key.strip().upper() == "ROTA_SUGERIDA":
            suggested_route = value.strip()

    output_upper = output.upper()
    if "RESPOSTA:" in output_upper:
        response_start = output_upper.index("RESPOSTA:") + len("RESPOSTA:")
        response = output[response_start:].strip()

    return {
        "messages": [AIMessage(content=response)],
        "called_agents": ["orchestrator"],
        "orchestrator_status": status,
        "suggested_route": suggested_route,
    }
