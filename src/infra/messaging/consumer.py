import asyncio
import logging
import socket
from collections.abc import Mapping
from uuid import uuid4

from redis.exceptions import ResponseError

from src.core.config.settings import settings
from src.infra.messaging.event import AgentEvent
from src.infra.messaging.redis_client import get_redis_client
from src.infra.messaging.result_store import save_event_result
from src.workflow.event_handler import handle_chat_event

logger = logging.getLogger(__name__)


def generate_consumer_name() -> str:
    hostname = socket.gethostname()
    unique_suffix = uuid4().hex[:8]

    return f"{settings.AGENT_CONSUMER_PREFIX}:" f"{hostname}:" f"{unique_suffix}"


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


async def run_consumer(
    stop_event: asyncio.Event,
    consumer_name: str | None = None,
) -> None:
    await ensure_consumer_group()

    redis = get_redis_client()
    name = consumer_name or generate_consumer_name()

    while not stop_event.is_set():
        messages = await redis.xreadgroup(
            groupname=settings.AGENT_STREAM_GROUP,
            consumername=name,
            streams={settings.AGENT_STREAM_CHATBOT: ">"},
            count=settings.AGENT_CONSUMER_BATCH_SIZE,
            block=settings.AGENT_CONSUMER_BLOCK_MS,
        )

        for _, stream_messages in messages:
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
