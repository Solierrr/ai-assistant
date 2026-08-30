import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from redis.exceptions import ResponseError

from src.infra.messaging import consumer
from src.infra.messaging.event import AgentEvent


def configure_stream_reader(monkeypatch, redis):
    redis.aclose = AsyncMock()
    factory = Mock(return_value=redis)
    monkeypatch.setattr(consumer, "create_redis_client", factory)
    return factory


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


async def test_recover_pending_messages_reivindica_e_processa_pendentes(
    monkeypatch,
):
    pending_messages = [("1700000000000-0", {"event_id": "event-123"})]
    redis = Mock()
    redis.xautoclaim = AsyncMock(
        return_value=["0-0", pending_messages, []],
    )
    process_stream_messages = AsyncMock()
    monkeypatch.setattr(consumer, "get_redis_client", Mock(return_value=redis))
    monkeypatch.setattr(
        consumer,
        "process_stream_messages",
        process_stream_messages,
    )

    await consumer.recover_pending_messages("consumer-1")

    redis.xautoclaim.assert_awaited_once_with(
        name=consumer.settings.AGENT_STREAM_CHATBOT,
        groupname=consumer.settings.AGENT_STREAM_GROUP,
        consumername="consumer-1",
        min_idle_time=consumer.settings.AGENT_CONSUMER_CLAIM_IDLE_MS,
        start_id="0-0",
        count=consumer.settings.AGENT_CONSUMER_BATCH_SIZE,
    )
    process_stream_messages.assert_awaited_once_with(pending_messages)


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
    recover_pending_messages = AsyncMock()
    reader_factory = configure_stream_reader(monkeypatch, redis)
    monkeypatch.setattr(
        consumer,
        "process_stream_message",
        process_stream_message,
    )
    monkeypatch.setattr(
        consumer,
        "recover_pending_messages",
        recover_pending_messages,
    )

    await consumer.run_consumer(stop_event, consumer_name="consumer-1")

    reader_factory.assert_called_once_with(
        socket_timeout_seconds=(consumer.settings.AGENT_CONSUMER_BLOCK_MS / 1_000 + 5),
        max_connections=1,
    )
    recover_pending_messages.assert_awaited_once_with("consumer-1")
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
    redis.aclose.assert_awaited_once_with()


async def test_run_consumer_registra_falha_e_mantem_execucao(monkeypatch):
    stop_event = asyncio.Event()
    redis = Mock()

    async def read_once(**kwargs):
        stop_event.set()
        return [("stream", [("message-1", {})])]

    redis.xreadgroup = AsyncMock(side_effect=read_once)
    process_stream_message = AsyncMock(side_effect=RuntimeError("Falha no agente"))
    logger = Mock()
    configure_stream_reader(monkeypatch, redis)
    monkeypatch.setattr(
        consumer,
        "process_stream_message",
        process_stream_message,
    )
    monkeypatch.setattr(consumer, "recover_pending_messages", AsyncMock())
    monkeypatch.setattr(consumer, "logger", logger)

    await consumer.run_consumer(stop_event, consumer_name="consumer-1")

    logger.exception.assert_called_once_with(
        "Falha ao processar mensagem %s",
        "message-1",
    )


async def test_run_consumer_propaga_cancelamento(monkeypatch):
    stop_event = asyncio.Event()
    redis = Mock()
    redis.xreadgroup = AsyncMock(return_value=[("stream", [("message-1", {})])])
    configure_stream_reader(monkeypatch, redis)
    monkeypatch.setattr(
        consumer,
        "process_stream_message",
        AsyncMock(side_effect=asyncio.CancelledError),
    )
    monkeypatch.setattr(consumer, "recover_pending_messages", AsyncMock())

    with pytest.raises(asyncio.CancelledError):
        await consumer.run_consumer(stop_event, consumer_name="consumer-1")


async def test_run_consumer_registra_falha_do_claim_e_continua_leitura(
    monkeypatch,
):
    stop_event = asyncio.Event()
    redis = Mock()

    async def read_once(**kwargs):
        stop_event.set()
        return []

    redis.xreadgroup = AsyncMock(side_effect=read_once)
    logger = Mock()
    recover_pending_messages = AsyncMock(
        side_effect=ConnectionError("Redis indisponível"),
    )
    configure_stream_reader(monkeypatch, redis)
    monkeypatch.setattr(
        consumer,
        "recover_pending_messages",
        recover_pending_messages,
    )
    monkeypatch.setattr(consumer, "logger", logger)

    await consumer.run_consumer(stop_event, consumer_name="consumer-1")

    logger.exception.assert_called_once_with("Falha ao recuperar mensagens pendentes")
    redis.xreadgroup.assert_awaited_once()


async def test_run_consumer_respeita_intervalo_entre_claims(monkeypatch):
    stop_event = asyncio.Event()
    redis = Mock()
    read_count = 0

    async def read_twice(**kwargs):
        nonlocal read_count
        read_count += 1
        if read_count == 2:
            stop_event.set()
        return []

    redis.xreadgroup = AsyncMock(side_effect=read_twice)
    recover_pending_messages = AsyncMock()
    sleep = AsyncMock()
    configure_stream_reader(monkeypatch, redis)
    monkeypatch.setattr(
        consumer,
        "recover_pending_messages",
        recover_pending_messages,
    )
    monkeypatch.setattr(
        consumer,
        "monotonic",
        Mock(side_effect=[100.0, 100.0, 101.0]),
    )
    monkeypatch.setattr(consumer.asyncio, "sleep", sleep)

    await consumer.run_consumer(stop_event, consumer_name="consumer-1")

    recover_pending_messages.assert_awaited_once_with("consumer-1")
    assert redis.xreadgroup.await_count == 2
    sleep.assert_awaited_once_with(
        consumer.settings.AGENT_CONSUMER_IDLE_DELAY_MS / 1_000
    )


async def test_run_consumer_repete_leitura_apos_falha_do_redis(monkeypatch):
    stop_event = asyncio.Event()
    redis = Mock()
    read_count = 0

    async def read_with_retry(**kwargs):
        nonlocal read_count
        read_count += 1
        if read_count == 1:
            raise ConnectionError("Redis indisponível")
        stop_event.set()
        return []

    redis.xreadgroup = AsyncMock(side_effect=read_with_retry)
    sleep = AsyncMock()
    logger = Mock()
    configure_stream_reader(monkeypatch, redis)
    monkeypatch.setattr(consumer, "recover_pending_messages", AsyncMock())
    monkeypatch.setattr(consumer.asyncio, "sleep", sleep)
    monkeypatch.setattr(consumer, "logger", logger)

    await consumer.run_consumer(stop_event, consumer_name="consumer-1")

    assert redis.xreadgroup.await_count == 2
    sleep.assert_awaited_once_with(
        consumer.settings.AGENT_CONSUMER_RETRY_DELAY_MS / 1_000
    )
    logger.exception.assert_called_once_with("Falha ao ler mensagens do Redis Stream")
