import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from redis.exceptions import ResponseError

from src.infra.messaging import consumer
from src.infra.messaging.event import AgentEvent


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


async def test_process_stream_message_salva_resultado_e_confirma_mensagem(
    monkeypatch,
):
    redis = Mock()
    redis.xack = AsyncMock(return_value=1)
    save_event_result = AsyncMock()
    handle_chat_event = AsyncMock(
        return_value={
            "status": "completed",
            "response": "Resposta final",
        }
    )
    monkeypatch.setattr(consumer, "get_redis_client", Mock(return_value=redis))
    monkeypatch.setattr(consumer, "save_event_result", save_event_result)
    monkeypatch.setattr(consumer, "handle_chat_event", handle_chat_event)
    event = AgentEvent(
        event_type="chatbot.message.received",
        payload={"conversation_id": "conversation-1", "message": "Olá"},
    )

    await consumer.process_stream_message("1700000000000-0", event.to_stream_fields())

    assert save_event_result.await_args_list[0].args == (
        event.event_id,
        {"status": "processing"},
    )
    assert save_event_result.await_args_list[1].args == (
        event.event_id,
        {"status": "completed", "response": "Resposta final"},
    )
    handle_chat_event.assert_awaited_once()
    processed_event = handle_chat_event.await_args.args[0]
    assert processed_event == event
    redis.xack.assert_awaited_once_with(
        consumer.settings.AGENT_STREAM_CHATBOT,
        consumer.settings.AGENT_STREAM_GROUP,
        "1700000000000-0",
    )


async def test_process_stream_message_nao_confirma_quando_handler_falha(
    monkeypatch,
):
    redis = Mock()
    redis.xack = AsyncMock()
    save_event_result = AsyncMock()
    handle_chat_event = AsyncMock(side_effect=RuntimeError("Falha no agente"))
    monkeypatch.setattr(consumer, "get_redis_client", Mock(return_value=redis))
    monkeypatch.setattr(consumer, "save_event_result", save_event_result)
    monkeypatch.setattr(consumer, "handle_chat_event", handle_chat_event)
    event = AgentEvent(
        event_type="chatbot.message.received",
        payload={"conversation_id": "conversation-1", "message": "Olá"},
    )

    with pytest.raises(RuntimeError, match="Falha no agente"):
        await consumer.process_stream_message(
            "1700000000000-0",
            event.to_stream_fields(),
        )

    save_event_result.assert_awaited_once_with(
        event.event_id,
        {"status": "processing"},
    )
    redis.xack.assert_not_awaited()


async def test_run_consumer_le_mensagens_novas_do_grupo(monkeypatch):
    stop_event = asyncio.Event()
    fields = {"event_id": "event-123"}
    redis = Mock()

    async def read_once(**kwargs):
        stop_event.set()
        return [
            (
                consumer.settings.AGENT_STREAM_CHATBOT,
                [("1700000000000-0", fields)],
            )
        ]

    redis.xreadgroup = AsyncMock(side_effect=read_once)
    process_stream_message = AsyncMock()
    ensure_consumer_group = AsyncMock()
    monkeypatch.setattr(consumer, "get_redis_client", Mock(return_value=redis))
    monkeypatch.setattr(
        consumer,
        "ensure_consumer_group",
        ensure_consumer_group,
    )
    monkeypatch.setattr(
        consumer,
        "process_stream_message",
        process_stream_message,
    )

    await consumer.run_consumer(stop_event, consumer_name="consumer-1")

    ensure_consumer_group.assert_awaited_once_with()
    redis.xreadgroup.assert_awaited_once_with(
        groupname=consumer.settings.AGENT_STREAM_GROUP,
        consumername="consumer-1",
        streams={consumer.settings.AGENT_STREAM_CHATBOT: ">"},
        count=consumer.settings.AGENT_CONSUMER_BATCH_SIZE,
        block=consumer.settings.AGENT_CONSUMER_BLOCK_MS,
    )
    process_stream_message.assert_awaited_once_with(
        "1700000000000-0",
        fields,
    )


async def test_run_consumer_registra_falha_e_mantem_execucao(monkeypatch):
    stop_event = asyncio.Event()
    redis = Mock()

    async def read_once(**kwargs):
        stop_event.set()
        return [("stream", [("message-1", {})])]

    redis.xreadgroup = AsyncMock(side_effect=read_once)
    process_stream_message = AsyncMock(side_effect=RuntimeError("Falha no agente"))
    logger = Mock()
    monkeypatch.setattr(consumer, "get_redis_client", Mock(return_value=redis))
    monkeypatch.setattr(consumer, "ensure_consumer_group", AsyncMock())
    monkeypatch.setattr(
        consumer,
        "process_stream_message",
        process_stream_message,
    )
    monkeypatch.setattr(consumer, "logger", logger)

    await consumer.run_consumer(stop_event, consumer_name="consumer-1")

    logger.exception.assert_called_once_with(
        "Falha ao processar mensagem %s",
        "message-1",
    )


async def test_run_consumer_propaga_cancelamento(monkeypatch):
    stop_event = asyncio.Event()
    redis = Mock()
    redis.xreadgroup = AsyncMock(
        return_value=[("stream", [("message-1", {})])]
    )
    monkeypatch.setattr(consumer, "get_redis_client", Mock(return_value=redis))
    monkeypatch.setattr(consumer, "ensure_consumer_group", AsyncMock())
    monkeypatch.setattr(
        consumer,
        "process_stream_message",
        AsyncMock(side_effect=asyncio.CancelledError),
    )

    with pytest.raises(asyncio.CancelledError):
        await consumer.run_consumer(stop_event, consumer_name="consumer-1")
