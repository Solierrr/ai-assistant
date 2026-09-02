from langchain_core.messages import AIMessage

from src.agents.base.base_agent import build_agent
from src.agents.specialist.solar_panel_specialist.solar_panel_specialist_prompt import (
    SOLAR_PANEL_SPECIALIST_AGENT,
)
from src.infra.mcp.client import get_mcp_tool
from src.workflow.nodes.context import messages_with_summary
from src.workflow.state import GraphState
from src.workflow.turn_tracking import append_turn_agent


async def solar_panel_specialist_node(state: GraphState, config=None) -> dict:
    tools = await get_mcp_tool("listar_ofertas_de_placas")
    agent = build_agent(SOLAR_PANEL_SPECIALIST_AGENT, tools=tools)
    result = await agent.ainvoke(
        {"messages": messages_with_summary(state)}, config=config
    )
    last_message = result["messages"][-1]

    return {
        "messages": [AIMessage(content=last_message.content)],
        "turn_agents": append_turn_agent(state, "solar_panel_specialist"),
    }
