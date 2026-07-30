import operator
from typing import Annotated

from langgraph.graph import MessagesState


class GraphState(MessagesState):
    route: str
    called_agents: Annotated[list[str], operator.add]
    summary: str
    pii_map: dict
