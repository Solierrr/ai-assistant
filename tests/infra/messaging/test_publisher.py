from unittest.mock import AsyncMock, Mock

import pytest

from src.infra.messaging import publisher
from src.infra.messaging.event import AgentEvent


async def test_publish_event_writes_event_and_initial_result_atomically(monkeypatch):
    pipeline = Mock()
    pipeline.execute = AsyncMock(return_value=["1720000000000-0", True])
    redis = Mock()
    redis.pipeline.return_value = pipeline
    monkeypatch.setattr(publisher, "get_redis_client", Mock(return_value=redis))
    event = AgentEvent(
        event_type="chatbot.message.received",
        payload={"conversation_id": "conversation-123", "message": "Preciso de ajuda"},
    )

    stream_id = await publisher.publish_event(event, {"status": "queued"})

    assert stream_id == "1720000000000-0"
    pipeline.xadd.assert_called_once()
    pipeline.set.assert_called_once()
    pipeline.execute.assert_awaited_once()


async def test_publish_event_propagates_redis_failure(monkeypatch):
    pipeline = Mock()
    pipeline.execute = AsyncMock(side_effect=ConnectionError("Redis indisponivel"))
    redis = Mock()
    redis.pipeline.return_value = pipeline
    monkeypatch.setattr(publisher, "get_redis_client", Mock(return_value=redis))

    with pytest.raises(ConnectionError, match="Redis indisponivel"):
        await publisher.publish_event(
            AgentEvent(event_type="chatbot.message.received", payload={}),
            {"status": "queued"},
        )
