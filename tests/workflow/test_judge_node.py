from unittest.mock import Mock

from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage, SystemMessage

import src.workflow.nodes.judge_node as judge_node


def _mock_llm(status, justificativa="justificativa qualquer"):
    veredito = judge_node.VereditoJuiz(status=status, justificativa=justificativa)
    structured_llm = Mock()
    structured_llm.invoke.return_value = veredito
    llm = Mock()
    llm.with_structured_output.return_value = structured_llm
    return llm


def test_judge_node_approves_when_status_aprovado(monkeypatch):
    llm = _mock_llm("APROVADO", "resposta coerente")
    monkeypatch.setattr(judge_node, "llm_groq", Mock(return_value=llm))

    resultado = judge_node.judge_node(
        {"messages": [AIMessage(content="Resposta final", id="msg-1")]}
    )

    assert resultado["judge_status"] == "approved"
    assert resultado["turn_agents"] == ["judge_approved"]
    assert "messages" not in resultado

    mensagens_enviadas = llm.with_structured_output.return_value.invoke.call_args.args[0]
    assert isinstance(mensagens_enviadas[0], SystemMessage)
    assert isinstance(mensagens_enviadas[1], HumanMessage)
    assert "Resposta final" in mensagens_enviadas[1].content


def test_judge_node_retries_once_when_rejected(monkeypatch):
    llm = _mock_llm("REPROVADO", "contem alucinacao")
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
    llm = _mock_llm("REPROVADO", "ainda incoerente")
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


def test_judge_node_fails_closed_for_unknown_status(monkeypatch):
    # Mesma lógica do input_guardrail: o schema garante que `status` sempre
    # existe, mas não garante que seja um dos valores esperados. Qualquer
    # coisa diferente de APROVADO segue o caminho de retry/bloqueio.
    llm = _mock_llm("STATUS_INESPERADO")
    monkeypatch.setattr(judge_node, "llm_groq", Mock(return_value=llm))

    resultado = judge_node.judge_node(
        {"messages": [AIMessage(content="Resposta", id="msg-1")], "judge_retries": 0}
    )

    assert resultado["judge_status"] == "retry"
