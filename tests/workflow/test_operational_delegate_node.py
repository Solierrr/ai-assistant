import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from ai_lib.a2a import DelegationError, DelegationResult
from langchain_core.messages import AIMessage, HumanMessage

import src.workflow.nodes.operational_delegate_node as node
from src.core.security.request_context import current_persona, current_user_token
from src.workflow.nodes import router_node

CONFIG = {"configurable": {"thread_id": "conversa-1"}}
STATE = {"messages": [HumanMessage(content="cadastra a placa X")]}


@pytest.fixture(autouse=True)
def _identidade():
    token = current_user_token.set("jwt-do-usuario")
    persona = current_persona.set("demandante")
    yield
    current_user_token.reset(token)
    current_persona.reset(persona)


def _delegate(monkeypatch, outcome="completed", text="Feito."):
    mock = AsyncMock(
        return_value=DelegationResult(
            outcome=outcome, text=text, task_id="t1", context_id="conversa-1"
        )
    )
    monkeypatch.setattr(node, "delegate", mock)
    return mock


def test_delegacao_repassa_texto_token_persona_e_conversa(monkeypatch):
    mock = _delegate(monkeypatch)

    result = asyncio.run(node.operational_delegate_node(STATE, CONFIG))

    mock.assert_awaited_once_with(
        node.settings.A2A_OPERATIONAL_URL,
        "cadastra a placa X",
        token="jwt-do-usuario",
        persona="demandante",
        context_id="conversa-1",
    )
    assert result["messages"][0].content == "Feito."
    assert result["turn_agents"] == ["operational_delegate"]
    assert result["awaiting_decision"] is False


def test_proposta_deixa_a_decisao_pendente(monkeypatch):
    _delegate(
        monkeypatch, outcome="input_required", text="Vou cadastrar a placa X. Aceita?"
    )

    result = asyncio.run(node.operational_delegate_node(STATE, CONFIG))

    assert result["messages"][0].content == "Vou cadastrar a placa X. Aceita?"
    assert result["awaiting_decision"] is True


def test_sem_token_nao_delega(monkeypatch):
    mock = _delegate(monkeypatch)
    current_user_token.set(None)

    result = asyncio.run(node.operational_delegate_node(STATE, CONFIG))

    mock.assert_not_awaited()
    assert "autenticado" in result["messages"][0].content
    assert result["awaiting_decision"] is False


def test_agente_remoto_fora_do_ar_responde_com_aviso(monkeypatch):
    monkeypatch.setattr(
        node, "delegate", AsyncMock(side_effect=DelegationError("fora"))
    )

    result = asyncio.run(node.operational_delegate_node(STATE, CONFIG))

    assert "Não consegui falar" in result["messages"][0].content
    assert result["awaiting_decision"] is False


@pytest.mark.parametrize("outcome", ["failed", "rejected", "canceled", "unknown"])
def test_desfecho_sem_sucesso_responde_com_aviso(monkeypatch, outcome):
    _delegate(monkeypatch, outcome=outcome, text="detalhe interno")

    result = asyncio.run(node.operational_delegate_node(STATE, CONFIG))

    assert "Não consegui falar" in result["messages"][0].content
    assert result["awaiting_decision"] is False


def test_usa_a_ultima_mensagem_do_usuario(monkeypatch):
    mock = _delegate(monkeypatch)
    state = {
        "messages": [
            HumanMessage(content="cadastra a placa X"),
            AIMessage(content="Vou cadastrar. Aceita?"),
            HumanMessage(content="sim"),
        ]
    }

    asyncio.run(node.operational_delegate_node(state, CONFIG))

    assert mock.await_args.args[1] == "sim"


def test_decisao_pendente_volta_direto_ao_agente_operacional(monkeypatch):
    llm = Mock()
    monkeypatch.setattr(router_node, "llm_groq", Mock(return_value=llm))
    state = {"messages": [HumanMessage(content="sim")], "awaiting_decision": True}

    result = router_node.router_node(state)

    assert result == {"route": "operational_delegate", "turn_agents": ["router"]}
    llm.invoke.assert_not_called()


def test_decisao_pendente_ja_consultada_nao_entra_em_laco(monkeypatch):
    monkeypatch.setattr(router_node, "llm_groq", Mock())
    state = {
        "messages": [HumanMessage(content="sim")],
        "awaiting_decision": True,
        "turn_agents": ["operational_delegate"],
    }

    result = router_node.router_node(state)

    assert result["route"] == "orchestrator"
