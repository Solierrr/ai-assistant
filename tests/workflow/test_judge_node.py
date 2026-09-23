from types import SimpleNamespace
from unittest.mock import Mock

from langchain_core.messages import AIMessage

import src.workflow.nodes.judge_node as node


def structured_llm(result):
    llm = Mock()
    llm.with_structured_output.return_value.invoke.return_value = result
    return llm


def test_judge_approves_structured_verdict(monkeypatch):
    monkeypatch.setattr(node, "llm_groq", Mock(return_value=structured_llm(SimpleNamespace(status="APROVADO", justificativa="ok"))))

    result = node.judge_node({"messages": [AIMessage(content="Resposta", id="1")]})

    assert result["judge_status"] == "approved"


def test_judge_retries_rejected_answer(monkeypatch):
    monkeypatch.setattr(node, "llm_groq", Mock(return_value=structured_llm(SimpleNamespace(status="REPROVADO", justificativa="erro"))))

    result = node.judge_node({"messages": [AIMessage(content="Resposta", id="1")], "judge_retries": 0})

    assert result["judge_status"] == "retry"
