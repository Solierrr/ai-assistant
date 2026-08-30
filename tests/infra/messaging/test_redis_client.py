from unittest.mock import AsyncMock, Mock

import pytest
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff

from src.infra.messaging import redis_client


@pytest.fixture(autouse=True)
def reset_redis_client(monkeypatch):
    redis_client._redis_client = None
    monkeypatch.setattr(
        redis_client.settings,
        "UPSTASH_REDIS_HOST",
        "redis.test",
    )
    monkeypatch.setattr(
        redis_client.settings,
        "UPSTASH_REDIS_PASSWORD",
        "token",
    )
    yield
    redis_client._redis_client = None


async def test_connect_redis_cria_cliente_e_executa_ping(monkeypatch):
    client = Mock()
    client.ping = AsyncMock(return_value=True)
    client.aclose = AsyncMock()

    redis_factory = Mock(return_value=client)
    monkeypatch.setattr(redis_client, "Redis", redis_factory)

    result = await redis_client.connect_redis()

    assert result is client
    client.ping.assert_awaited_once()

    redis_factory.assert_called_once_with(
        host=redis_client.settings.UPSTASH_REDIS_HOST,
        port=redis_client.settings.UPSTASH_REDIS_PORT,
        username=redis_client.settings.UPSTASH_REDIS_USERNAME,
        password=redis_client.settings.UPSTASH_REDIS_PASSWORD,
        ssl=True,
        decode_responses=True,
        socket_timeout=5.0,
        socket_connect_timeout=5.0,
        max_connections=10,
        retry=Retry(NoBackoff(), 0),
    )


def test_create_redis_client_aceita_timeout_para_leitura_bloqueante(monkeypatch):
    redis_factory = Mock(return_value=Mock())
    monkeypatch.setattr(redis_client, "Redis", redis_factory)

    redis_client.create_redis_client(
        socket_timeout_seconds=65.0,
        max_connections=1,
    )

    call = redis_factory.call_args.kwargs
    assert call["socket_timeout"] == 65.0
    assert call["socket_connect_timeout"] == 5.0
    assert call["max_connections"] == 1
    assert call["retry"] == Retry(NoBackoff(), 0)


async def test_connect_redis_reutiliza_cliente_existente(monkeypatch):
    client = Mock()
    redis_client._redis_client = client

    redis_factory = Mock()
    monkeypatch.setattr(redis_client, "Redis", redis_factory)

    result = await redis_client.connect_redis()

    assert result is client
    redis_factory.assert_not_called()


def test_get_redis_client_falha_sem_conexao():
    with pytest.raises(
        RuntimeError,
        match="Conexão com o Redis ainda não foi estabelecida",
    ):
        redis_client.get_redis_client()


def test_get_redis_client_retorna_cliente_existente():
    client = Mock()
    redis_client._redis_client = client

    assert redis_client.get_redis_client() is client


async def test_close_redis_fecha_e_limpa_cliente():
    client = Mock()
    client.aclose = AsyncMock()
    redis_client._redis_client = client

    await redis_client.close_redis()

    client.aclose.assert_awaited_once()
    assert redis_client._redis_client is None


async def test_connect_redis_fecha_cliente_quando_ping_falha(monkeypatch):
    client = Mock()
    client.ping = AsyncMock(side_effect=ConnectionError("Redis indisponível"))
    client.aclose = AsyncMock()

    monkeypatch.setattr(redis_client, "Redis", Mock(return_value=client))

    with pytest.raises(ConnectionError, match="Redis indisponível"):
        await redis_client.connect_redis()

    client.aclose.assert_awaited_once()
    assert redis_client._redis_client is None


async def test_connect_redis_falha_quando_credenciais_nao_estao_configuradas(
    monkeypatch,
):
    redis_factory = Mock()
    monkeypatch.setattr(redis_client.settings, "UPSTASH_REDIS_HOST", None)
    monkeypatch.setattr(redis_client.settings, "UPSTASH_REDIS_PASSWORD", None)
    monkeypatch.setattr(redis_client, "Redis", redis_factory)

    with pytest.raises(RuntimeError, match="Credenciais do Upstash Redis"):
        await redis_client.connect_redis()

    redis_factory.assert_not_called()
