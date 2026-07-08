from langgraph.graph import StateGraph, END

from src.workflow.state import Estado
from src.workflow.nodes import (
    no_guardrail_entrada,
    no_roteador,
    no_orquestrador,
    no_guardrail_saida,
    no_condensar_historico,
)
from src.workflow.edges import decidir_pos_entrada, decidir_pos_roteador
from src.memory.session.mongo_checkpointer import criar_checkpointer_mongo

grafo = StateGraph(Estado)

grafo.add_node("guardrail_entrada", no_guardrail_entrada)
grafo.add_node("condensar_memoria", no_condensar_historico)
grafo.add_node("roteador", no_roteador)
grafo.add_node("orquestrador", no_orquestrador)
grafo.add_node("guardrail_saida", no_guardrail_saida)

grafo.set_entry_point("guardrail_entrada")

grafo.add_conditional_edges(
    "guardrail_entrada",
    decidir_pos_entrada,
    {"prosseguir": "condensar_memoria", "fim": END},
)

grafo.add_edge("condensar_memoria", "roteador")

grafo.add_conditional_edges(
    "roteador", decidir_pos_roteador, {"prosseguir": "orquestrador", "fim": END}
)

grafo.add_edge("orquestrador", "guardrail_saida")
grafo.add_edge("guardrail_saida", END)

memory = criar_checkpointer_mongo()

app_fluxo = grafo.compile(checkpointer=memory)
