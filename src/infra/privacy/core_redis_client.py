from redis.asyncio import Redis

from src.core.config.settings import settings

_core_redis: Redis | None = None


def create_core_redis_client() -> Redis:
    if not settings.UPSTASH_CORE_HOST or not settings.UPSTASH_CORE_PASSWORD:
        raise RuntimeError("Credenciais UPSTASH_CORE_* não configuradas.")
    return Redis(
        host=settings.UPSTASH_CORE_HOST,
        port=settings.UPSTASH_CORE_PORT,
        username=settings.UPSTASH_CORE_USERNAME,
        password=settings.UPSTASH_CORE_PASSWORD,
        ssl=True,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        health_check_interval=0,
        max_connections=10,
    )


async def connect_core_redis() -> Redis:
    global _core_redis
    if _core_redis is None:
        client = create_core_redis_client()
        try:
            await client.ping()
        except Exception:
            await client.aclose()
            raise
        _core_redis = client
    return _core_redis


def get_core_redis() -> Redis:
    if _core_redis is None:
        raise RuntimeError("Conexão com solaria-core ainda não foi estabelecida.")
    return _core_redis


async def close_core_redis() -> None:
    global _core_redis
    if _core_redis is not None:
        await _core_redis.aclose()
        _core_redis = None
