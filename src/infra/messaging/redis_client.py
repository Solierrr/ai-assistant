from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff

from src.core.config.settings import settings

_redis_client: Redis | None = None


def create_redis_client(
    *,
    socket_timeout_seconds: float = 5.0,
    max_connections: int = 10,
) -> Redis:
    if not settings.UPSTASH_REDIS_HOST or not settings.UPSTASH_REDIS_PASSWORD:
        raise RuntimeError("Credenciais do Upstash Redis não configuradas.")

    return Redis(
        host=settings.UPSTASH_REDIS_HOST,
        port=settings.UPSTASH_REDIS_PORT,
        username=settings.UPSTASH_REDIS_USERNAME,
        password=settings.UPSTASH_REDIS_PASSWORD,
        ssl=True,
        decode_responses=True,
        socket_timeout=socket_timeout_seconds,
        socket_connect_timeout=5.0,
        max_connections=max_connections,
        retry=Retry(NoBackoff(), 0),
    )


async def connect_redis() -> Redis:
    global _redis_client

    if _redis_client is not None:
        return _redis_client

    client = create_redis_client()

    try:
        await client.ping()
    except Exception:
        await client.aclose()
        raise
    _redis_client = client
    return _redis_client


def get_redis_client() -> Redis:
    if _redis_client is None:
        raise RuntimeError("Conexão com o Redis ainda não foi estabelecida.")
    return _redis_client


async def close_redis() -> None:
    global _redis_client

    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
