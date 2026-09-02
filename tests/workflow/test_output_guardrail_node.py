from unittest.mock import Mock

from langchain_core.messages import AIMessage, RemoveMessage

from src.agents.base.system_prompt import SYSTEM_CORE_COMMUNICATION, SYSTEM_CORE_SECURITY
import src.workflow.nodes.output_guardrail_node as output_guardrail_node


def _mock_llm(resposta_revisada, foi_corrigida):
    revisao = output_guardrail_node.RevisaoCompliance(
        resposta_revisada=resposta_revisada, foi_corrigida=foi_corrigida
    )
    structured_llm = Mock()
    structured_llm.invoke.return_value = revisao
    llm = Mock()
    llm.with_structured_output.return_value = structured_llm
    return llm


def test_output_guardrail_prompt_omits_communication_standards():
    assert SYSTEM_CORE_SECURITY.strip() in output_guardrail_node.OUTPUT_GUARDRAIL_PROMPT
    assert (
        SYSTEM_CORE_COMMUNICATION.strip()
        not in output_guardrail_node.OUTPUT_GUARDRAIL_PROMPT
    )


def test_output_guardrail_node_deanonymizes_corrected_response(monkeypatch):
    llm = _mock_llm("Olá, [PII_NOME].", foi_corrigida=True)
    deanonymize = Mock(return_value="Olá, Ana.")
    monkeypatch.setattr(output_guardrail_node, "llm_groq", Mock(return_value=llm))
    monkeypatch.setattr(output_guardrail_node, "deanonymize_text", deanonymize)
    mensagem = AIMessage(content="Resposta do agente", id="msg-1")

    resultado = output_guardrail_node.output_guardrail_node(
        {
            "messages": [mensagem],
            "pii_map": {"[PII_NOME]": "Ana"},
            "turn_agents": ["router", "solar_panel_specialist", "orchestrator"],
        }
    )

    assert resultado["turn_agents"] == [
        "router",
        "solar_panel_specialist",
        "orchestrator",
        "output_guardrail",
    ]
    assert isinstance(resultado["messages"][0], RemoveMessage)
    assert resultado["messages"][0].id == "msg-1"
    assert isinstance(resultado["messages"][1], AIMessage)
    assert resultado["messages"][1].additional_kwargs == {
        "specialists_used": ["solar_panel_specialist"],
        "workflow_steps": resultado["turn_agents"],
    }
    assert resultado["messages"][1].content == "Olá, Ana."
    deanonymize.assert_called_once_with("Olá, [PII_NOME].", {"[PII_NOME]": "Ana"})


def test_output_guardrail_node_preserves_response_without_correction(monkeypatch):
    llm = _mock_llm("Resposta revisada", foi_corrigida=False)
    deanonymize = Mock(return_value="Resposta revisada")
    monkeypatch.setattr(output_guardrail_node, "llm_groq", Mock(return_value=llm))
    monkeypatch.setattr(output_guardrail_node, "deanonymize_text", deanonymize)
    mensagem = AIMessage(content="Resposta do agente", id="msg-2")

    resultado = output_guardrail_node.output_guardrail_node(
        {"messages": [mensagem], "pii_map": {}, "turn_agents": ["router"]}
    )

    assert resultado["messages"][1].content == "Resposta revisada"
    deanonymize.assert_called_once_with("Resposta revisada", {})
