from types import SimpleNamespace
from unittest.mock import Mock

from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage, SystemMessage

import src.workflow.nodes.judge_node as judge_node


def _mock_llm(content):
    llm = Mock()
    llm.invoke.return_value = SimpleNamespace(content=content)
    return llm


def test_judge_node_approves_when_status_aprovado(monkeypatch):
    llm = _mock_llm("STATUS: APROVADO\nJUSTIFICATIVA: resposta coerente")
    monkeypatch.setattr(judge_node, "llm_groq", Mock(return_value=llm))

    resultado = judge_node.judge_node(
        {"messages": [AIMessage(content="Resposta final", id="msg-1")]}
    )

    assert resultado["judge_status"] == "approved"
    assert resultado["turn_agents"] == ["judge_approved"]
    assert "messages" not in resultado

    mensagens_enviadas = llm.invoke.call_args.args[0]
    assert isinstance(mensagens_enviadas[0], SystemMessage)
    assert isinstance(mensagens_enviadas[1], HumanMessage)
    assert "Resposta final" in mensagens_enviadas[1].content


def test_judge_node_retries_once_when_rejected(monkeypatch):
    llm = _mock_llm("STATUS: REPROVADO\nJUSTIFICATIVA: contem alucinacao")
    monkeypatch.setattr(judge_node, "llm_groq", Mock(return_value=llm))

    resultado = judge_node.judge_node(
        {
            "messages": [AIMessage(content="Resposta duvidosa", id="msg-1")],
            "judge_retries": 0,
        }
    )

    assert resultado["judge_status"] == "retry"
    assert resultado["judge_retries"] == 1
    assert resultado["turn_agents"] == ["judge_rejected"]
    assert isinstance(resultado["messages"][0], RemoveMessage)


def test_judge_node_blocks_after_exhausting_retries(monkeypatch):
    llm = _mock_llm("STATUS: REPROVADO\nJUSTIFICATIVA: ainda incoerente")
    monkeypatch.setattr(judge_node, "llm_groq", Mock(return_value=llm))

    resultado = judge_node.judge_node(
        {
            "messages": [AIMessage(content="Resposta ruim", id="msg-1")],
            "judge_retries": 1,
        }
    )

    assert resultado["judge_status"] == "blocked"
    assert resultado["turn_agents"] == ["judge_blocked"]
    assert isinstance(resultado["messages"][0], RemoveMessage)
    assert isinstance(resultado["messages"][1], AIMessage)
    assert resultado["messages"][1].content == judge_node.BLOCKED_RESPONSE


def test_judge_node_defaults_to_retry_when_status_malformed(monkeypatch):
    llm = _mock_llm("resposta sem o rotulo esperado")
    monkeypatch.setattr(judge_node, "llm_groq", Mock(return_value=llm))

    resultado = judge_node.judge_node(
        {"messages": [AIMessage(content="Resposta", id="msg-1")], "judge_retries": 0}
    )

    assert resultado["judge_status"] == "retry"
