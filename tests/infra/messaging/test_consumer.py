import asyncio
from unittest.mock import AsyncMock, Mock

from redis.exceptions import ResponseError

from src.infra.messaging import consumer
from src.infra.messaging.event import AgentEvent


async def test_ensure_consumer_group_ignores_existing_group(monkeypatch):
    redis = Mock()
    redis.xgroup_create = AsyncMock(side_effect=ResponseError("BUSYGROUP already exists"))
    monkeypatch.setattr(consumer, "get_redis_client", Mock(return_value=redis))

    await consumer.ensure_consumer_group()

    redis.xgroup_create.assert_awaited_once()


async def test_process_stream_message_stores_metrics_then_acknowledges(monkeypatch):
    redis = Mock()
    redis.xack = AsyncMock(return_value=1)
    save_result = AsyncMock()
    handle_event = AsyncMock(return_value={"status": "completed", "response": "Resposta"})
    monkeypatch.setattr(consumer, "get_redis_client", Mock(return_value=redis))
    monkeypatch.setattr(consumer, "save_event_result", save_result)
    monkeypatch.setattr(consumer, "handle_chat_event", handle_event)
    event = AgentEvent(
        event_type="chatbot.message.received",
        payload={
            "conversation_id": "thread-1",
            "messenger_conversation_id": "messenger-1",
            "message": "Oi",
        },
    )

    await consumer.process_stream_message("1-0", event.to_stream_fields())

    assert save_result.await_count == 2
    assert save_result.await_args_list[0].args[1]["status"] == "processing"
    assert save_result.await_args_list[1].args[1]["status"] == "completed"
    assert "total_time_ms" in save_result.await_args_list[1].args[1]
    redis.xack.assert_awaited_once()


async def test_processing_failure_is_terminal_and_acknowledged(monkeypatch):
    redis = Mock()
    redis.xack = AsyncMock(return_value=1)
    redis.xdel = AsyncMock(return_value=1)
    save_result = AsyncMock()
    monkeypatch.setattr(consumer, "get_redis_client", Mock(return_value=redis))
    monkeypatch.setattr(consumer, "save_event_result", save_result)

    await consumer.handle_processing_failure("1-0", {"event_id": "event-1"})

    assert save_result.await_args.args[1]["status"] == "failed"
    redis.xack.assert_awaited_once()
    redis.xdel.assert_awaited_once()


async def test_second_consumer_does_not_claim_pending_messages(monkeypatch):
    stop_event = asyncio.Event()
    redis = Mock()

    async def stop_after_read(**_kwargs):
        stop_event.set()
        return []

    redis.xreadgroup = AsyncMock(side_effect=stop_after_read)
    redis.aclose = AsyncMock()
    monkeypatch.setattr(consumer, "create_redis_client", Mock(return_value=redis))
    recover_pending = AsyncMock()
    monkeypatch.setattr(consumer, "recover_pending_messages", recover_pending)

    await consumer.run_consumer(stop_event, consumer_name="consumer-2", recover_pending=False)

    recover_pending.assert_not_awaited()
