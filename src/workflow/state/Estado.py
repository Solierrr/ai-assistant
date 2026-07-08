from typing import Annotated
import operator
from langgraph.graph import MessagesState


class Estado(MessagesState):
    rota: str
    agentes_chamados: Annotated[list[str], operator.add]
    resumo: str
    pii_map: dict
