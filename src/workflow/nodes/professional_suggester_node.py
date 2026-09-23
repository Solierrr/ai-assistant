from langchain_core.messages import AIMessage

from src.agents.base.base_agent import invoke_agent_with_fallback
from src.agents.specialist.professional_suggester.professional_suggester_prompt import (
    PROFESSIONAL_SUGGESTER_AGENT,
)
from src.infra.mcp.client import get_mcp_tool
from src.workflow.nodes.context import messages_with_summary
from src.workflow.state import GraphState
from src.workflow.turn_tracking import append_turn_agent


async def professional_suggester_node(state: GraphState, config=None) -> dict:
    tools = await get_mcp_tool("buscar_tecnicos_credenciados")
    result = await invoke_agent_with_fallback(
        PROFESSIONAL_SUGGESTER_AGENT,
        messages_with_summary(state),
        tools=tools,
        config=config,
    )
    last_message = result["messages"][-1]

    return {
        "messages": [AIMessage(content=last_message.content)],
        "turn_agents": append_turn_agent(state, "professional_suggester"),
    }
