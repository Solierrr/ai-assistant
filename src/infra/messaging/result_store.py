import json
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from src.core.config.settings import settings
from src.infra.messaging.redis_client import get_redis_client


def build_result_key(event_id: UUID | str) -> str:
    return f"{settings.AGENT_RESULT_PREFIX}:{event_id}"

async def save_event_result(
    event_id: UUID | str,
    result: Mapping[str, Any],
) -> None:
    redis = get_redis_client()
    stored_result = {
        **dict(result),
        "event_id": str(event_id),
    }

    await redis.set(
        name=build_result_key(event_id),
        value=json.dumps(stored_result, ensure_ascii=False),
        ex=settings.AGENT_RESULT_TTL_SECONDS,
    )

async def get_event_result(
    event_id: UUID | str,
) -> dict[str, Any] | None:
    redis = get_redis_client()
    stored_result = await redis.get(build_result_key(event_id))

    if stored_result is None:
        return None
    return json.loads(stored_result)

async def delete_event_result(event_id: UUID | str) -> None:
    redis = get_redis_client()
    await redis.delete(build_result_key(event_id))