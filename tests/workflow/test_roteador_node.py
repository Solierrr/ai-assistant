from types import SimpleNamespace
from unittest.mock import Mock

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.agents.base.system_prompt import SYSTEM_CORE_COMUNICACAO, SYSTEM_CORE_SEGURANCA
from src.agents.specialist.router.router_prompt import ROUTER_AGENT
from src.workflow.nodes import roteador_node


def _mock_llm(content):
    llm = Mock()
    llm.invoke.return_value = SimpleNamespace(content=content)
    return llm


def test_no_roteador_extrai_rota_quando_llm_retorna_route(monkeypatch):
    llm = _mock_llm("ROUTE=solar_panel_specialist\nJUSTIFICATIVA=pedido tecnico")
    monkeypatch.setattr(roteador_node, "llm_groq", Mock(return_value=llm))

    resultado = roteador_node.no_roteador(
        {"messages": [HumanMessage(content="Preciso de paineis solares")]}
    )

    assert resultado == {
        "rota": "solar_panel_specialist",
        "agentes_chamados": ["roteador"],
    }

    mensagens_enviadas = llm.invoke.call_args.args[0]
    assert isinstance(mensagens_enviadas[0], SystemMessage)
    assert SYSTEM_CORE_SEGURANCA.strip() in mensagens_enviadas[0].content
    assert SYSTEM_CORE_COMUNICACAO.strip() in mensagens_enviadas[0].content
    assert ROUTER_AGENT.strip() in mensagens_enviadas[0].content
    assert isinstance(mensagens_enviadas[1], HumanMessage)


def test_no_roteador_responde_diretamente_quando_nao_ha_route(monkeypatch):
    llm = _mock_llm("Posso ajudar com informacoes sobre a Solaria.")
    monkeypatch.setattr(roteador_node, "llm_groq", Mock(return_value=llm))

    resultado = roteador_node.no_roteador(
        {"messages": [HumanMessage(content="O que e a Solaria?")]}
    )

    assert resultado["rota"] == "fim"
    assert resultado["agentes_chamados"] == ["roteador_resposta_direta"]
    assert len(resultado["messages"]) == 1
    assert isinstance(resultado["messages"][0], AIMessage)
    assert resultado["messages"][0].content == "Posso ajudar com informacoes sobre a Solaria."
