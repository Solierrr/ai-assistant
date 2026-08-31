import asyncio
import logging
import socket
from collections.abc import Iterable, Mapping
from time import monotonic
from uuid import uuid4

from redis.exceptions import ResponseError

from src.core.config.settings import settings
from src.infra.messaging.event import AgentEvent
from src.infra.messaging.redis_client import (
    create_redis_client,
    get_redis_client,
)
from src.infra.messaging.result_store import save_event_result
from src.workflow.event_handler import handle_chat_event

logger = logging.getLogger(__name__)


def generate_consumer_name() -> str:
    hostname = socket.gethostname()
    unique_suffix = uuid4().hex[:8]

    return f"{settings.AGENT_CONSUMER_PREFIX}:{hostname}:{unique_suffix}"


async def ensure_consumer_group() -> None:
    redis = get_redis_client()

    try:
        await redis.xgroup_create(
            name=settings.AGENT_STREAM_CHATBOT,
            groupname=settings.AGENT_STREAM_GROUP,
            id="0-0",
            mkstream=True,
        )
    except ResponseError as error:
        if "BUSYGROUP" not in str(error):
            raise


async def process_stream_message(
    message_id: str,
    fields: Mapping[str, str],
) -> None:
    redis = get_redis_client()
    event = AgentEvent.from_stream_fields(fields)

    await save_event_result(
        event.event_id,
        {"status": "processing"},
    )

    result = await handle_chat_event(event)
    await save_event_result(event.event_id, result)

    await redis.xack(
        settings.AGENT_STREAM_CHATBOT,
        settings.AGENT_STREAM_GROUP,
        message_id,
    )


async def get_delivery_count(message_id: str) -> int:
    redis = get_redis_client()
    pending = await redis.xpending_range(
        name=settings.AGENT_STREAM_CHATBOT,
        groupname=settings.AGENT_STREAM_GROUP,
        min=message_id,
        max=message_id,
        count=1,
    )

    if not pending or pending[0]["message_id"] != message_id:
        return 1
    return int(pending[0]["times_delivered"])


async def handle_processing_failure(
    message_id: str,
    fields: Mapping[str, str],
) -> None:
    redis = get_redis_client()
    attempts = await get_delivery_count(message_id)
    event_id = fields.get("event_id")

    if attempts < settings.AGENT_CONSUMER_MAX_ATTEMPTS:
        if event_id:
            await save_event_result(
                event_id,
                {
                    "status": "retrying",
                    "attempts": attempts,
                    "max_attempts": settings.AGENT_CONSUMER_MAX_ATTEMPTS,
                },
            )
        return

    if event_id:
        await save_event_result(
            event_id,
            {
                "status": "failed",
                "error": "Não foi possível processar a mensagem.",
                "attempts": attempts,
                "max_attempts": settings.AGENT_CONSUMER_MAX_ATTEMPTS,
            },
        )

    await redis.xack(
        settings.AGENT_STREAM_CHATBOT,
        settings.AGENT_STREAM_GROUP,
        message_id,
    )
    await redis.xdel(settings.AGENT_STREAM_CHATBOT, message_id)


async def process_stream_messages(
    stream_messages: Iterable[tuple[str, Mapping[str, str]]],
) -> None:
    for message_id, fields in stream_messages:
        try:
            await process_stream_message(message_id, fields)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(
                "Falha ao processar mensagem %s",
                message_id,
            )
            try:
                await handle_processing_failure(message_id, fields)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "Falha ao registrar tentativa da mensagem %s",
                    message_id,
                )


async def recover_pending_messages(consumer_name: str) -> None:
    redis = get_redis_client()

    claimed = await redis.xautoclaim(
        name=settings.AGENT_STREAM_CHATBOT,
        groupname=settings.AGENT_STREAM_GROUP,
        consumername=consumer_name,
        min_idle_time=settings.AGENT_CONSUMER_CLAIM_IDLE_MS,
        start_id="0-0",
        count=settings.AGENT_CONSUMER_BATCH_SIZE,
    )

    await process_stream_messages(claimed[1])


async def run_consumer(
    stop_event: asyncio.Event,
    consumer_name: str | None = None,
) -> None:
    read_timeout_seconds = settings.AGENT_CONSUMER_BLOCK_MS / 1_000 + 5
    redis = create_redis_client(
        socket_timeout_seconds=read_timeout_seconds,
        max_connections=1,
    )
    name = consumer_name or generate_consumer_name()

    claim_interval_seconds = settings.AGENT_CONSUMER_CLAIM_INTERVAL_MS / 1_000
    last_claim_at = monotonic() - claim_interval_seconds

    try:
        while not stop_event.is_set():
            current_time = monotonic()

            if current_time - last_claim_at >= claim_interval_seconds:
                last_claim_at = current_time

                try:
                    await recover_pending_messages(name)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("Falha ao recuperar mensagens pendentes")

            try:
                messages = await redis.xreadgroup(
                    groupname=settings.AGENT_STREAM_GROUP,
                    consumername=name,
                    streams={settings.AGENT_STREAM_CHATBOT: ">"},
                    count=settings.AGENT_CONSUMER_BATCH_SIZE,
                    block=settings.AGENT_CONSUMER_BLOCK_MS,
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Falha ao ler mensagens do Redis Stream")
                await asyncio.sleep(settings.AGENT_CONSUMER_RETRY_DELAY_MS / 1_000)
                continue

            if not messages:
                if not stop_event.is_set():
                    await asyncio.sleep(settings.AGENT_CONSUMER_IDLE_DELAY_MS / 1_000)
                continue

            for _, stream_messages in messages:
                await process_stream_messages(stream_messages)
    finally:
        await redis.aclose()
