from types import SimpleNamespace
from unittest.mock import Mock

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.agents.base.system_prompt import SYSTEM_CORE_COMMUNICATION, SYSTEM_CORE_SECURITY
from src.agents.specialist.orchestrator.orchestrator_prompt import ORCHESTRATOR_AGENT
import src.workflow.nodes.orchestrator_node as orchestrator_node


def test_orchestrator_node_uses_prompt_and_fallback(monkeypatch):
    gemini = Mock()
    groq = Mock()
    llm_com_fallback = Mock()
    llm_com_fallback.invoke.return_value = SimpleNamespace(
        content="STATUS: SUFICIENTE\nRESPOSTA: Resposta final"
    )
    gemini.with_fallbacks.return_value = llm_com_fallback
    monkeypatch.setattr(orchestrator_node, "llm_gemini", Mock(return_value=gemini))
    monkeypatch.setattr(orchestrator_node, "llm_groq", Mock(return_value=groq))

    resultado = orchestrator_node.orchestrator_node(
        {"route": "qualquer", "messages": [HumanMessage(content="Olá")]}
    )

    assert resultado["called_agents"] == ["orchestrator"]
    assert resultado["orchestrator_status"] == "SUFICIENTE"
    assert resultado["suggested_route"] == ""
    assert isinstance(resultado["messages"][0], AIMessage)
    assert resultado["messages"][0].content == "Resposta final"
    gemini.with_fallbacks.assert_called_once_with([groq])
    mensagens = llm_com_fallback.invoke.call_args.args[0]
    assert isinstance(mensagens[0], SystemMessage)
    assert SYSTEM_CORE_SECURITY.strip() in mensagens[0].content
    assert SYSTEM_CORE_COMMUNICATION.strip() in mensagens[0].content
    assert ORCHESTRATOR_AGENT.strip() in mensagens[0].content
    assert isinstance(mensagens[1], HumanMessage)


def test_orchestrator_node_extracts_support_status_and_keeps_summary_in_context(
    monkeypatch,
):
    gemini = Mock()
    groq = Mock()
    llm_com_fallback = Mock()
    llm_com_fallback.invoke.return_value = SimpleNamespace(
        content=(
            "STATUS: PRECISA_APOIO\n"
            "ROTA_SUGERIDA: faq_reader\n"
            "RESPOSTA: Preciso confirmar a garantia."
        )
    )
    gemini.with_fallbacks.return_value = llm_com_fallback
    monkeypatch.setattr(orchestrator_node, "llm_gemini", Mock(return_value=gemini))
    monkeypatch.setattr(orchestrator_node, "llm_groq", Mock(return_value=groq))

    resultado = orchestrator_node.orchestrator_node(
        {
            "messages": [HumanMessage(content="Qual a garantia?")],
            "summary": "O usuário quer informações sobre painéis solares.",
        }
    )

    assert resultado["orchestrator_status"] == "PRECISA_APOIO"
    assert resultado["suggested_route"] == "faq_reader"
    assert resultado["messages"][0].content == "Preciso confirmar a garantia."
    mensagens = llm_com_fallback.invoke.call_args.args[0]
    assert "Resumo" in mensagens[1].content
    assert isinstance(mensagens[2], HumanMessage)
