from langgraph.graph import END, StateGraph

from src.memory.session.mongo_checkpointer import create_mongo_checkpointer
from src.workflow.edges import decide_post_input_guardrail, decide_post_router
from src.workflow.nodes.agency_suggester_node import agency_suggester_node
from src.workflow.nodes.faq_reader_node import faq_reader_node
from src.workflow.nodes.input_guardrail_node import input_guardrail_node
from src.workflow.nodes.orchestrator_node import orchestrator_node
from src.workflow.nodes.output_guardrail_node import output_guardrail_node
from src.workflow.nodes.professional_suggester_node import professional_suggester_node
from src.workflow.nodes.router_node import router_node
from src.workflow.nodes.solar_panel_specialist_node import solar_panel_specialist_node
from src.workflow.nodes.summary_node import condense_history_node
from src.workflow.state import GraphState

graph = StateGraph(GraphState)

graph.add_node("input_guardrail", input_guardrail_node)
graph.add_node("condense_memory", condense_history_node)
graph.add_node("router", router_node)
graph.add_node("faq_reader", faq_reader_node)
graph.add_node("professional_suggester", professional_suggester_node)
graph.add_node("agency_suggester", agency_suggester_node)
graph.add_node("solar_panel_specialist", solar_panel_specialist_node)
graph.add_node("orchestrator", orchestrator_node)
graph.add_node("output_guardrail", output_guardrail_node)

graph.set_entry_point("input_guardrail")

graph.add_conditional_edges(
    "input_guardrail",
    decide_post_input_guardrail,
    {"proceed": "condense_memory", "end": END},
)

graph.add_edge("condense_memory", "router")

graph.add_conditional_edges(
    "router",
    decide_post_router,
    {
        "faq_reader": "faq_reader",
        "professional_suggester": "professional_suggester",
        "agency_suggester": "agency_suggester",
        "solar_panel_specialist": "solar_panel_specialist",
        "orchestrator": "orchestrator",
        "end": "output_guardrail",
    },
)

graph.add_edge("faq_reader", "router")
graph.add_edge("professional_suggester", "router")
graph.add_edge("agency_suggester", "router")
graph.add_edge("solar_panel_specialist", "router")
graph.add_edge("orchestrator", "output_guardrail")
graph.add_edge("output_guardrail", END)

memory = create_mongo_checkpointer()

compiled_app = graph.compile(checkpointer=memory)
