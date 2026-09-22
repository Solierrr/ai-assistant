import logging

from redis.asyncio import Redis

from src.core.config.settings import settings

logger = logging.getLogger(__name__)

_redis_client: Redis | None = None


def create_redis_client(
    *,
    socket_timeout_seconds: float | None = 5.0,
    max_connections: int | None = 10,
) -> Redis:
    if not settings.UPSTASH_AGENTS_HOST or not settings.UPSTASH_AGENTS_PASSWORD:
        raise RuntimeError("Credenciais UPSTASH_AGENTS_* não configuradas.")

    return Redis(
        host=settings.UPSTASH_AGENTS_HOST,
        port=settings.UPSTASH_AGENTS_PORT,
        username=settings.UPSTASH_AGENTS_USERNAME,
        password=settings.UPSTASH_AGENTS_PASSWORD,
        ssl=True,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=socket_timeout_seconds,
        retry_on_timeout=False,
        health_check_interval=0,
        max_connections=max_connections,
    )


async def connect_redis() -> Redis:
    global _redis_client

    if _redis_client is None:
        client = create_redis_client()
        try:
            await client.ping()
        except Exception:
            await client.aclose()
            raise
        _redis_client = client
        logger.info("Redis dos agentes conectado")
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
        logger.info("Redis dos agentes desconectado")
