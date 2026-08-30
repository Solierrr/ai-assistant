import socket
from uuid import uuid4

from redis.exceptions import ResponseError

from src.core.config.settings import settings
from src.infra.messaging.redis_client import get_redis_client


def generate_consumer_name() -> str:
    hostname = socket.gethostname()
    unique_suffix = uuid4().hex[:8]

    return (
        f"{settings.AGENT_CONSUMER_PREFIX}:"
        f"{hostname}:"
        f"{unique_suffix}"
    )


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
