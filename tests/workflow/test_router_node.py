from types import SimpleNamespace
from unittest.mock import Mock

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.agents.base.system_prompt import SYSTEM_CORE_COMMUNICATION, SYSTEM_CORE_SECURITY
from src.agents.specialist.router.router_prompt import ROUTER_AGENT
import src.workflow.nodes.router_node as router_node


def _mock_llm(content):
    llm = Mock()
    llm.invoke.return_value = SimpleNamespace(content=content)
    return llm


def test_router_node_extracts_route_when_llm_returns_route(monkeypatch):
    llm = _mock_llm("ROUTE=solar_panel_specialist\nJUSTIFICATIVA=pedido tecnico")
    monkeypatch.setattr(router_node, "llm_groq", Mock(return_value=llm))

    resultado = router_node.router_node(
        {"messages": [HumanMessage(content="Preciso de paineis solares")]}
    )

    assert resultado == {
        "route": "solar_panel_specialist",
        "called_agents": ["router"],
    }

    mensagens_enviadas = llm.invoke.call_args.args[0]
    assert isinstance(mensagens_enviadas[0], SystemMessage)
    assert SYSTEM_CORE_SECURITY.strip() in mensagens_enviadas[0].content
    assert SYSTEM_CORE_COMMUNICATION.strip() in mensagens_enviadas[0].content
    assert ROUTER_AGENT.strip() in mensagens_enviadas[0].content
    assert "Rotas" in mensagens_enviadas[1].content
    assert isinstance(mensagens_enviadas[2], HumanMessage)


def test_router_node_includes_summary_and_only_offers_unused_routes(monkeypatch):
    llm = _mock_llm("ROUTE=faq_reader")
    monkeypatch.setattr(router_node, "llm_groq", Mock(return_value=llm))

    router_node.router_node(
        {
            "messages": [HumanMessage(content="Preciso de ajuda")],
            "summary": "O usuário já recebeu orientação técnica.",
            "called_agents": ["solar_panel_specialist"],
            "suggested_route": "faq_reader",
        }
    )

    mensagens_enviadas = llm.invoke.call_args.args[0]
    assert "faq_reader" in mensagens_enviadas[1].content
    assert "solar_panel_specialist" not in mensagens_enviadas[1].content
    assert "Resumo" in mensagens_enviadas[2].content
    assert isinstance(mensagens_enviadas[3], HumanMessage)


def test_router_node_responds_directly_when_no_route(monkeypatch):
    llm = _mock_llm("Posso ajudar com informacoes sobre a Solaria.")
    monkeypatch.setattr(router_node, "llm_groq", Mock(return_value=llm))

    resultado = router_node.router_node(
        {"messages": [HumanMessage(content="O que e a Solaria?")]}
    )

    assert resultado["route"] == "end"
    assert resultado["called_agents"] == ["router_direct_response"]
    assert len(resultado["messages"]) == 1
    assert isinstance(resultado["messages"][0], AIMessage)
    assert resultado["messages"][0].content == "Posso ajudar com informacoes sobre a Solaria."
