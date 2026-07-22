from types import SimpleNamespace
from unittest.mock import Mock

from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage

from src.agents.base.system_prompt import SYSTEM_CORE_COMMUNICATION, SYSTEM_CORE_SECURITY
import src.workflow.nodes.output_guardrail_node as output_guardrail_node


def _mock_llm(content):
    llm = Mock()
    llm.invoke.return_value = SimpleNamespace(content=content)
    return llm


def test_output_guardrail_prompt_omits_communication_standards():
    assert SYSTEM_CORE_SECURITY.strip() in output_guardrail_node.OUTPUT_GUARDRAIL_PROMPT
    assert (
        SYSTEM_CORE_COMMUNICATION.strip()
        not in output_guardrail_node.OUTPUT_GUARDRAIL_PROMPT
    )


def test_output_guardrail_node_extracts_and_deanonymizes_response(monkeypatch):
    llm = _mock_llm("STATUS: CORRIGIDO\n\nRESPOSTA:\nOlá, [PII_NOME].")
    deanonymize = Mock(return_value="Olá, Ana.")
    monkeypatch.setattr(output_guardrail_node, "llm_groq", Mock(return_value=llm))
    monkeypatch.setattr(output_guardrail_node, "deanonymize_text", deanonymize)
    mensagem = AIMessage(content="Resposta do agente", id="msg-1")

    resultado = output_guardrail_node.output_guardrail_node(
        {"messages": [mensagem], "pii_map": {"[PII_NOME]": "Ana"}}
    )

    assert resultado["called_agents"] == ["output_guardrail"]
    assert isinstance(resultado["messages"][0], RemoveMessage)
    assert resultado["messages"][0].id == "msg-1"
    assert isinstance(resultado["messages"][1], AIMessage)
    assert resultado["messages"][1].content == "Olá, Ana."
    deanonymize.assert_called_once_with("Olá, [PII_NOME].", {"[PII_NOME]": "Ana"})


def test_output_guardrail_node_preserves_text_without_header(monkeypatch):
    llm = _mock_llm("Resposta revisada")
    deanonymize = Mock(return_value="Resposta revisada")
    monkeypatch.setattr(output_guardrail_node, "llm_groq", Mock(return_value=llm))
    monkeypatch.setattr(output_guardrail_node, "deanonymize_text", deanonymize)
    mensagem = AIMessage(content="Resposta do agente", id="msg-2")

    resultado = output_guardrail_node.output_guardrail_node(
        {"messages": [mensagem], "pii_map": {}}
    )

    assert resultado["messages"][1].content == "Resposta revisada"
    deanonymize.assert_called_once_with("Resposta revisada", {})
