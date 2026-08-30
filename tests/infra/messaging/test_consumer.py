from unittest.mock import AsyncMock, Mock

import pytest
from redis.exceptions import ResponseError

from src.infra.messaging import consumer


def test_generate_consumer_name_combina_prefixo_hostname_e_uuid(monkeypatch):
    monkeypatch.setattr(
        consumer.socket,
        "gethostname",
        Mock(return_value="chatbot-pod-01"),
    )
    monkeypatch.setattr(
        consumer,
        "uuid4",
        Mock(return_value=Mock(hex="abcdef1234567890")),
    )

    consumer_name = consumer.generate_consumer_name()

    assert consumer_name == (
        f"{consumer.settings.AGENT_CONSUMER_PREFIX}:chatbot-pod-01:abcdef12"
    )


def test_generate_consumer_name_gera_sufixos_diferentes(monkeypatch):
    monkeypatch.setattr(
        consumer.socket,
        "gethostname",
        Mock(return_value="chatbot-pod-01"),
    )
    monkeypatch.setattr(
        consumer,
        "uuid4",
        Mock(
            side_effect=[
                Mock(hex="11111111aaaaaaaa"),
                Mock(hex="22222222bbbbbbbb"),
            ]
        ),
    )

    first_name = consumer.generate_consumer_name()
    second_name = consumer.generate_consumer_name()

    assert first_name != second_name


async def test_ensure_consumer_group_cria_grupo_e_stream(monkeypatch):
    redis = Mock()
    redis.xgroup_create = AsyncMock(return_value=True)
    monkeypatch.setattr(consumer, "get_redis_client", Mock(return_value=redis))

    await consumer.ensure_consumer_group()

    redis.xgroup_create.assert_awaited_once_with(
        name=consumer.settings.AGENT_STREAM_CHATBOT,
        groupname=consumer.settings.AGENT_STREAM_GROUP,
        id="0-0",
        mkstream=True,
    )


async def test_ensure_consumer_group_ignora_grupo_ja_existente(monkeypatch):
    redis = Mock()
    redis.xgroup_create = AsyncMock(
        side_effect=ResponseError("BUSYGROUP Consumer Group name already exists")
    )
    monkeypatch.setattr(consumer, "get_redis_client", Mock(return_value=redis))

    await consumer.ensure_consumer_group()

    redis.xgroup_create.assert_awaited_once()


async def test_ensure_consumer_group_propaga_outro_erro_do_redis(monkeypatch):
    redis = Mock()
    redis.xgroup_create = AsyncMock(side_effect=ResponseError("Redis indisponivel"))
    monkeypatch.setattr(consumer, "get_redis_client", Mock(return_value=redis))

    with pytest.raises(ResponseError, match="Redis indisponivel"):
        await consumer.ensure_consumer_group()


async def test_ensure_consumer_group_falha_sem_cliente_conectado(monkeypatch):
    get_client = Mock(
        side_effect=RuntimeError("Conexao com o Redis ainda nao foi estabelecida.")
    )
    monkeypatch.setattr(consumer, "get_redis_client", get_client)

    with pytest.raises(RuntimeError, match="Redis ainda nao foi estabelecida"):
        await consumer.ensure_consumer_group()

    get_client.assert_called_once_with()
