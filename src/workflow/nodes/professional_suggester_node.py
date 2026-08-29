from langchain_core.messages import AIMessage

from src.agents.base.base_agent import build_agent
from src.agents.specialist.professional_suggester.professional_suggester_prompt import (
    PROFESSIONAL_SUGGESTER_AGENT,
)
from src.infra.mcp.client import get_mcp_tool
from src.workflow.nodes.context import messages_with_summary
from src.workflow.state import GraphState
from src.workflow.turn_tracking import append_turn_agent


async def professional_suggester_node(state: GraphState) -> dict:
    tools = await get_mcp_tool("buscar_tecnicos_credenciados")
    agent = build_agent(PROFESSIONAL_SUGGESTER_AGENT, tools=tools)
    result = await agent.ainvoke({"messages": messages_with_summary(state)})
    last_message = result["messages"][-1]

    return {
        "messages": [AIMessage(content=last_message.content)],
        "turn_agents": append_turn_agent(state, "professional_suggester"),
    }
