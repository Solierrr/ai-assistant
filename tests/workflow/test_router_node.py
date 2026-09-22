from types import SimpleNamespace
from unittest.mock import Mock

from langchain_core.messages import HumanMessage

from src.workflow.nodes import router_node


def structured_llm(result):
    llm = Mock()
    llm.with_structured_output.return_value.invoke.return_value = result
    return llm


def test_router_uses_structured_specialist_route(monkeypatch):
    llm = structured_llm(SimpleNamespace(rota="faq_reader", resposta_direta=None))
    monkeypatch.setattr(router_node, "llm_groq", Mock(return_value=llm))

    result = router_node.router_node({"messages": [HumanMessage(content="Tenho uma duvida")]})

    assert result == {"route": "faq_reader", "turn_agents": ["router"]}
    llm.with_structured_output.assert_called_once_with(router_node.DecisaoRoteamento)


def test_router_returns_direct_response_without_route(monkeypatch):
    llm = structured_llm(SimpleNamespace(rota=None, resposta_direta="Resposta direta"))
    monkeypatch.setattr(router_node, "llm_groq", Mock(return_value=llm))

    result = router_node.router_node({"messages": [HumanMessage(content="Oi")]})

    assert result["route"] == "end"
    assert result["messages"][0].content == "Resposta direta"
