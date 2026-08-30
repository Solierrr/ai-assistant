from unittest.mock import AsyncMock, Mock

import pytest

from src.infra.messaging import publisher
from src.infra.messaging.event import AgentEvent


async def test_publish_event_adiciona_evento_ao_stream(monkeypatch):
    redis = Mock()
    redis.xadd = AsyncMock(return_value="1720000000000-0")
    monkeypatch.setattr(publisher, "get_redis_client", Mock(return_value=redis))

    event = AgentEvent(
        event_type="chatbot.message.received",
        payload={
            "conversation_id": "conversation-123",
            "message": "Preciso de ajuda",
        },
        metadata={"source": "api"},
    )

    stream_id = await publisher.publish_event(event)

    assert stream_id == "1720000000000-0"
    redis.xadd.assert_awaited_once_with(
        name=publisher.settings.AGENT_STREAM_CHATBOT,
        fields=event.to_stream_fields(),
        id="*",
        maxlen=publisher.settings.AGENT_STREAM_MAXLEN,
        approximate=True,
    )


async def test_publish_event_propaga_falha_do_redis(monkeypatch):
    redis = Mock()
    redis.xadd = AsyncMock(side_effect=ConnectionError("Redis indisponivel"))
    monkeypatch.setattr(publisher, "get_redis_client", Mock(return_value=redis))

    event = AgentEvent(event_type="chatbot.message.received", payload={})

    with pytest.raises(ConnectionError, match="Redis indisponivel"):
        await publisher.publish_event(event)

    redis.xadd.assert_awaited_once()


async def test_publish_event_falha_quando_cliente_nao_foi_conectado(monkeypatch):
    get_client = Mock(
        side_effect=RuntimeError("Conexao com o Redis ainda nao foi estabelecida.")
    )
    monkeypatch.setattr(publisher, "get_redis_client", get_client)

    event = AgentEvent(event_type="chatbot.message.received", payload={})

    with pytest.raises(RuntimeError, match="Redis ainda nao foi estabelecida"):
        await publisher.publish_event(event)

    get_client.assert_called_once_with()
