from types import SimpleNamespace
from unittest.mock import Mock

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.agents.base.system_prompt import SYSTEM_CORE_COMUNICACAO, SYSTEM_CORE_SEGURANCA
from src.agents.specialist.orchestrator.orchestrator_prompt import ORCHESTRATOR_AGENT
from src.workflow.nodes import orquestrador_node


def test_no_orquestrador_usa_prompt_e_fallback(monkeypatch):
    gemini = Mock()
    groq = Mock()
    llm_com_fallback = Mock()
    llm_com_fallback.invoke.return_value = SimpleNamespace(content="Resposta final")
    gemini.with_fallbacks.return_value = llm_com_fallback
    monkeypatch.setattr(orquestrador_node, "llm_gemini", Mock(return_value=gemini))
    monkeypatch.setattr(orquestrador_node, "llm_groq", Mock(return_value=groq))

    resultado = orquestrador_node.no_orquestrador(
        {"rota": "qualquer", "messages": [HumanMessage(content="Olá")]}
    )

    assert resultado["agentes_chamados"] == ["orquestrador"]
    assert isinstance(resultado["messages"][0], AIMessage)
    assert resultado["messages"][0].content == "Resposta final"
    gemini.with_fallbacks.assert_called_once_with([groq])
    mensagens = llm_com_fallback.invoke.call_args.args[0]
    assert isinstance(mensagens[0], SystemMessage)
    assert SYSTEM_CORE_SEGURANCA.strip() in mensagens[0].content
    assert SYSTEM_CORE_COMUNICACAO.strip() in mensagens[0].content
    assert ORCHESTRATOR_AGENT.strip() in mensagens[0].content
    assert isinstance(mensagens[1], HumanMessage)
