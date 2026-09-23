from langchain_core.messages import AIMessage, SystemMessage

from src.agents.base.base_agent import invoke_model_with_fallback
from src.agents.base.base_prompt import build_system_prompt
from src.agents.specialist.orchestrator.orchestrator_prompt import ORCHESTRATOR_AGENT
from src.workflow.nodes.context import messages_with_summary
from src.workflow.state import GraphState
from src.workflow.turn_tracking import append_turn_agent

ORCHESTRATOR_PROMPT = build_system_prompt(ORCHESTRATOR_AGENT)


async def orchestrator_node(state: GraphState, config=None) -> dict:
    messages_with_context = [
        SystemMessage(content=ORCHESTRATOR_PROMPT),
        *messages_with_summary(state),
    ]
    response = (
        await invoke_model_with_fallback(messages_with_context, config=config)
    ).content.strip()

    return {
        "messages": [AIMessage(content=response)],
        "turn_agents": append_turn_agent(state, "orchestrator"),
    }
