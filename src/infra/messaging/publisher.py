from src.core.config.settings import settings
from src.infra.messaging.event import AgentEvent
from src.infra.messaging.redis_client import get_redis_client


async def publish_event(event: AgentEvent) -> str:
    redis = get_redis_client()

    stream_id = await redis.xadd(
        name=settings.AGENT_STREAM_CHATBOT,
        fields=event.to_stream_fields(),
        id="*",
        maxlen=settings.AGENT_STREAM_MAXLEN,
        approximate=True,
    )

    return stream_id
