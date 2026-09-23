from collections.abc import Mapping
from typing import Any

from src.core.config.settings import settings
from src.infra.messaging.event import AgentEvent
from src.infra.messaging.redis_client import get_redis_client
from src.infra.messaging.result_store import build_result_key, serialize_event_result


async def publish_event(event: AgentEvent, initial_result: Mapping[str, Any]) -> str:
    pipeline = get_redis_client().pipeline(transaction=True)
    pipeline.xadd(
        name=settings.AGENT_STREAM_CHATBOT,
        fields=event.to_stream_fields(),
        id="*",
        maxlen=settings.AGENT_STREAM_MAXLEN,
        approximate=True,
    )
    pipeline.set(
        name=build_result_key(event.event_id),
        value=serialize_event_result(event.event_id, initial_result),
        ex=settings.AGENT_RESULT_TTL_SECONDS,
    )
    responses = await pipeline.execute()
    return str(responses[0])
