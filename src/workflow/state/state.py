from typing import Annotated
import operator
from langgraph.graph import MessagesState


class GraphState(MessagesState):
    route: str
    called_agents: Annotated[list[str], operator.add]
    summary: str
    pii_map: dict
