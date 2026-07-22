from langchain_core.messages import AIMessage, SystemMessage

from src.agents.base.base_prompt import build_system_prompt
from src.agents.specialist.router.router_prompt import ROUTER_AGENT
from src.core.llm.llm_groq import llm_groq
from src.workflow.state import GraphState

ROUTER_PROMPT = build_system_prompt(ROUTER_AGENT)


def router_node(state: GraphState) -> dict:
    messages_with_context = [SystemMessage(content=ROUTER_PROMPT)] + state["messages"]
    output = llm_groq().invoke(messages_with_context).content

    if "ROUTE=" in output:
        extracted_route = output.split("ROUTE=")[1].strip().splitlines()[0]
        return {"route": extracted_route, "called_agents": ["router"]}

    return {
        "messages": [AIMessage(content=output)],
        "route": "end",
        "called_agents": ["router_direct_response"],
    }
