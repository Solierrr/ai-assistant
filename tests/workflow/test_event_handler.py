from unittest.mock import AsyncMock, Mock

import pytest
from langchain_core.messages import AIMessage

from src.infra.messaging.event import AgentEvent
from src.workflow import event_handler


def event(payload: dict) -> AgentEvent:
    return AgentEvent(event_type=event_handler.CHATBOT_MESSAGE_RECEIVED, payload=payload)


async def test_handle_chat_event_executes_prepared_turn(monkeypatch):
    workflow = Mock()
    execute = AsyncMock(
        return_value={
            "messages": [
                AIMessage(
                    content="Resposta final",
                    additional_kwargs={"specialists_used": ["faq_reader"]},
                )
            ],
            "turn_agents": ["router", "faq_reader"],
        }
    )
    monkeypatch.setattr(event_handler, "execute_prepared_turn", execute)

    result = await event_handler.handle_chat_event(
        event(
            {
                "conversation_id": "thread-1",
                "messenger_conversation_id": "messenger-1",
                "message": "Como investir?",
            }
        ),
        workflow,
    )

    prepared_turn = execute.await_args.args[0]
    assert prepared_turn.thread_id == "thread-1"
    assert prepared_turn.messenger_conversation_id == "messenger-1"
    assert prepared_turn.user_input == "Como investir?"
    assert execute.await_args.args[1] is workflow
    assert result["status"] == "completed"
    assert result["workflow_steps"] == ["router", "faq_reader"]


@pytest.mark.parametrize(
    "payload, invalid_field",
    [
        ({"message": "Oi"}, "conversation_id"),
        ({"conversation_id": "thread", "message": "Oi"}, "messenger_conversation_id"),
        (
            {
                "conversation_id": "thread",
                "messenger_conversation_id": "messenger",
                "message": " ",
            },
            "message",
        ),
    ],
)
async def test_handle_chat_event_rejects_invalid_payload(monkeypatch, payload, invalid_field):
    execute = AsyncMock()
    monkeypatch.setattr(event_handler, "execute_prepared_turn", execute)

    with pytest.raises(ValueError, match=invalid_field):
        await event_handler.handle_chat_event(event(payload), Mock())

    execute.assert_not_awaited()
