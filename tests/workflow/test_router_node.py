from unittest.mock import Mock

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.agents.base.system_prompt import SYSTEM_CORE_COMMUNICATION, SYSTEM_CORE_SECURITY
from src.agents.specialist.router.router_prompt import ROUTER_AGENT
import src.workflow.nodes.router_node as router_node


def _mock_llm(rota, resposta_direta=None):
    decisao = router_node.DecisaoRoteamento(rota=rota, resposta_direta=resposta_direta)
    structured_llm = Mock()
    structured_llm.invoke.return_value = decisao
    llm = Mock()
    llm.with_structured_output.return_value = structured_llm
    return llm


def test_router_node_extracts_route_when_llm_returns_route(monkeypatch):
    llm = _mock_llm("solar_panel_specialist")
    monkeypatch.setattr(router_node, "llm_groq", Mock(return_value=llm))

    resultado = router_node.router_node(
        {"messages": [HumanMessage(content="Preciso de paineis solares")]}
    )

    assert resultado == {"route": "solar_panel_specialist", "turn_agents": ["router"]}

    mensagens_enviadas = llm.with_structured_output.return_value.invoke.call_args.args[0]
    assert isinstance(mensagens_enviadas[0], SystemMessage)
    assert SYSTEM_CORE_SECURITY.strip() in mensagens_enviadas[0].content
    assert SYSTEM_CORE_COMMUNICATION.strip() in mensagens_enviadas[0].content
    assert ROUTER_AGENT.strip() in mensagens_enviadas[0].content
    assert "Rotas" in mensagens_enviadas[1].content
    assert isinstance(mensagens_enviadas[2], HumanMessage)


def test_router_node_returns_route_to_orchestrator_when_llm_says_so(monkeypatch):
    llm = _mock_llm("orchestrator")
    monkeypatch.setattr(router_node, "llm_groq", Mock(return_value=llm))

    resultado = router_node.router_node(
        {
            "messages": [HumanMessage(content="Já respondeu tudo que eu precisava")],
            "turn_agents": ["solar_panel_specialist"],
        }
    )

    assert resultado["route"] == "orchestrator"
    assert resultado["turn_agents"] == ["solar_panel_specialist", "router"]


def test_router_node_only_offers_unused_routes(monkeypatch):
    llm = _mock_llm("faq_reader")
    monkeypatch.setattr(router_node, "llm_groq", Mock(return_value=llm))

    router_node.router_node(
        {
            "messages": [HumanMessage(content="Preciso de ajuda")],
            "summary": "O usuário já recebeu orientação técnica.",
            "turn_agents": ["solar_panel_specialist"],
        }
    )

    mensagens_enviadas = llm.with_structured_output.return_value.invoke.call_args.args[0]
    assert "faq_reader" in mensagens_enviadas[1].content
    assert "solar_panel_specialist" not in mensagens_enviadas[1].content
    assert "Resumo" in mensagens_enviadas[2].content
    assert isinstance(mensagens_enviadas[3], HumanMessage)


def test_router_node_responds_directly_when_no_route(monkeypatch):
    llm = _mock_llm(None, resposta_direta="Posso ajudar com informacoes sobre a Solaria.")
    monkeypatch.setattr(router_node, "llm_groq", Mock(return_value=llm))

    resultado = router_node.router_node(
        {"messages": [HumanMessage(content="O que e a Solaria?")]}
    )

    assert resultado["route"] == "end"
    assert resultado["turn_agents"] == ["router_direct_response"]
    assert len(resultado["messages"]) == 1
    assert isinstance(resultado["messages"][0], AIMessage)
    assert resultado["messages"][0].content == "Posso ajudar com informacoes sobre a Solaria."


def test_router_node_short_circuits_to_orchestrator_when_limit_reached(monkeypatch):
    llm = Mock()
    monkeypatch.setattr(router_node, "llm_groq", Mock(return_value=llm))
    monkeypatch.setattr(router_node.config, "MAX_SPECIALISTS_PER_REQUEST", 1)

    resultado = router_node.router_node(
        {
            "messages": [HumanMessage(content="Mais uma pergunta")],
            "turn_agents": ["faq_reader"],
        }
    )

    assert resultado["route"] == "orchestrator"
    llm.with_structured_output.assert_not_called()
