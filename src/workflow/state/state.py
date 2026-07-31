from langgraph.graph import MessagesState


class GraphState(MessagesState):
    route: str
    turn_agents: list[str]
    summary: str
    pii_map: dict
    orchestrator_status: str
    suggested_route: str
