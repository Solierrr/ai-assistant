from unittest.mock import AsyncMock, Mock

import pytest
from langchain_core.messages import AIMessage

from src.infra.messaging.event import AgentEvent
from src.workflow import event_handler


@pytest.mark.asyncio
async def test_handle_chat_event_processa_evento_e_retorna_resultado(monkeypatch):
    workflow = Mock()
    execute_turn = AsyncMock(
        return_value={
            "messages": [
                AIMessage(
                    content="Resposta final",
                    additional_kwargs={
                        "specialists_used": ["faq_reader"],
                        "workflow_steps": ["router", "faq_reader", "orchestrator"],
                    },
                )
            ],
            "turn_agents": ["router", "faq_reader"],
        }
    )
    monkeypatch.setattr(event_handler, "execute_turn", execute_turn)
    event = AgentEvent(
        event_type=event_handler.CHATBOT_MESSAGE_RECEIVED,
        payload={
            "conversation_id": "conversation-1",
            "message": "Como posso investir?",
        },
    )

    result = await event_handler.handle_chat_event(event, workflow)

    execute_turn.assert_awaited_once_with(
        "conversation-1",
        "Como posso investir?",
        workflow,
        event_id=str(event.event_id),
    )
    assert result == {
        "status": "completed",
        "conversation_id": "conversation-1",
        "response": "Resposta final",
        "specialists_used": ["faq_reader"],
        "workflow_steps": ["router", "faq_reader", "orchestrator"],
    }


@pytest.mark.asyncio
async def test_handle_chat_event_usa_turn_agents_quando_nao_ha_workflow_steps(
    monkeypatch,
):
    execute_turn = AsyncMock(
        return_value={
            "messages": [AIMessage(content="Resposta final")],
            "turn_agents": ["router", "orchestrator"],
        }
    )
    monkeypatch.setattr(event_handler, "execute_turn", execute_turn)
    event = AgentEvent(
        event_type=event_handler.CHATBOT_MESSAGE_RECEIVED,
        payload={"conversation_id": "conversation-1", "message": "Olá"},
    )

    result = await event_handler.handle_chat_event(event, Mock())

    assert result["specialists_used"] == []
    assert result["workflow_steps"] == ["router", "orchestrator"]


@pytest.mark.asyncio
async def test_handle_chat_event_rejeita_tipo_nao_suportado(monkeypatch):
    execute_turn = AsyncMock()
    monkeypatch.setattr(event_handler, "execute_turn", execute_turn)
    event = AgentEvent(event_type="chatbot.unknown", payload={})

    with pytest.raises(ValueError, match="Tipo do evento não suportado"):
        await event_handler.handle_chat_event(event, Mock())

    execute_turn.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("payload", "invalid_field"),
    [
        ({"message": "Olá"}, "conversation_id"),
        ({"conversation_id": "conversation-1", "message": "   "}, "message"),
        ({"conversation_id": 123, "message": "Olá"}, "conversation_id"),
    ],
)
async def test_handle_chat_event_rejeita_payload_invalido(
    monkeypatch,
    payload,
    invalid_field,
):
    execute_turn = AsyncMock()
    monkeypatch.setattr(event_handler, "execute_turn", execute_turn)
    event = AgentEvent(
        event_type=event_handler.CHATBOT_MESSAGE_RECEIVED,
        payload=payload,
    )

    with pytest.raises(ValueError, match=invalid_field):
        await event_handler.handle_chat_event(event, Mock())

    execute_turn.assert_not_awaited()
