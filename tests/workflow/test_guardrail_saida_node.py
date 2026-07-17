from types import SimpleNamespace
from unittest.mock import Mock

from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage

from src.agents.base.system_prompt import SYSTEM_CORE_COMUNICACAO, SYSTEM_CORE_SEGURANCA
from src.workflow.nodes import guardrail_saida_node


def _mock_llm(content):
    llm = Mock()
    llm.invoke.return_value = SimpleNamespace(content=content)
    return llm


def test_prompt_do_guardrail_saida_omite_padrao_de_comunicacao():
    assert SYSTEM_CORE_SEGURANCA.strip() in guardrail_saida_node.PROMPT_GUARDRAIL_SAIDA
    assert (
        SYSTEM_CORE_COMUNICACAO.strip()
        not in guardrail_saida_node.PROMPT_GUARDRAIL_SAIDA
    )


def test_no_guardrail_saida_extrai_resposta_e_desanonimiza(monkeypatch):
    llm = _mock_llm("STATUS: CORRIGIDO\n\nRESPOSTA:\nOlá, [PII_NOME].")
    desanonimizar = Mock(return_value="Olá, Ana.")
    monkeypatch.setattr(guardrail_saida_node, "llm_groq", Mock(return_value=llm))
    monkeypatch.setattr(guardrail_saida_node, "desanonimizar_texto", desanonimizar)
    mensagem = AIMessage(content="Resposta do agente", id="msg-1")

    resultado = guardrail_saida_node.no_guardrail_saida(
        {"messages": [mensagem], "pii_map": {"[PII_NOME]": "Ana"}}
    )

    assert resultado["agentes_chamados"] == ["guardrail_saida"]
    assert isinstance(resultado["messages"][0], RemoveMessage)
    assert resultado["messages"][0].id == "msg-1"
    assert isinstance(resultado["messages"][1], AIMessage)
    assert resultado["messages"][1].content == "Olá, Ana."
    desanonimizar.assert_called_once_with("Olá, [PII_NOME].", {"[PII_NOME]": "Ana"})


def test_no_guardrail_saida_preserva_texto_quando_nao_ha_cabecalho(monkeypatch):
    llm = _mock_llm("Resposta revisada")
    desanonimizar = Mock(return_value="Resposta revisada")
    monkeypatch.setattr(guardrail_saida_node, "llm_groq", Mock(return_value=llm))
    monkeypatch.setattr(guardrail_saida_node, "desanonimizar_texto", desanonimizar)
    mensagem = AIMessage(content="Resposta do agente", id="msg-2")

    resultado = guardrail_saida_node.no_guardrail_saida(
        {"messages": [mensagem], "pii_map": {}}
    )

    assert resultado["messages"][1].content == "Resposta revisada"
    desanonimizar.assert_called_once_with("Resposta revisada", {})
