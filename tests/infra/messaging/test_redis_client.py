from unittest.mock import AsyncMock, Mock

import pytest

from src.infra.messaging import redis_client


@pytest.fixture(autouse=True)
def reset_redis_client(monkeypatch):
    redis_client._redis_client = None
    monkeypatch.setattr(redis_client.settings, "UPSTASH_AGENTS_HOST", "redis.test")
    monkeypatch.setattr(redis_client.settings, "UPSTASH_AGENTS_PASSWORD", "secret")
    yield
    redis_client._redis_client = None


def test_create_redis_client_usa_namespace_de_credenciais_dos_agentes(monkeypatch):
    redis_factory = Mock()
    monkeypatch.setattr(redis_client, "Redis", redis_factory)

    redis_client.create_redis_client(
        socket_timeout_seconds=70,
        max_connections=1,
    )

    redis_factory.assert_called_once_with(
        host=redis_client.settings.UPSTASH_AGENTS_HOST,
        port=redis_client.settings.UPSTASH_AGENTS_PORT,
        username=redis_client.settings.UPSTASH_AGENTS_USERNAME,
        password=redis_client.settings.UPSTASH_AGENTS_PASSWORD,
        ssl=True,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=70,
        health_check_interval=0,
        max_connections=1,
    )


def test_create_redis_client_falha_sem_credenciais(monkeypatch):
    monkeypatch.setattr(redis_client.settings, "UPSTASH_AGENTS_HOST", None)

    with pytest.raises(RuntimeError, match="UPSTASH_AGENTS"):
        redis_client.create_redis_client()


async def test_connect_redis_cria_cliente_e_executa_ping(monkeypatch):
    client = Mock(ping=AsyncMock(return_value=True), aclose=AsyncMock())
    monkeypatch.setattr(redis_client, "create_redis_client", Mock(return_value=client))

    result = await redis_client.connect_redis()

    assert result is client
    client.ping.assert_awaited_once()


async def test_connect_redis_reutiliza_cliente_existente(monkeypatch):
    client = Mock()
    redis_client._redis_client = client
    factory = Mock()
    monkeypatch.setattr(redis_client, "create_redis_client", factory)

    assert await redis_client.connect_redis() is client
    factory.assert_not_called()


def test_get_redis_client_falha_sem_conexao():
    with pytest.raises(RuntimeError, match="Redis ainda não foi estabelecida"):
        redis_client.get_redis_client()


async def test_close_redis_fecha_e_limpa_cliente():
    client = Mock(aclose=AsyncMock())
    redis_client._redis_client = client

    await redis_client.close_redis()

    client.aclose.assert_awaited_once()
    assert redis_client._redis_client is None


async def test_connect_redis_fecha_cliente_quando_ping_falha(monkeypatch):
    client = Mock(
        ping=AsyncMock(side_effect=ConnectionError("Redis indisponível")),
        aclose=AsyncMock(),
    )
    monkeypatch.setattr(redis_client, "create_redis_client", Mock(return_value=client))

    with pytest.raises(ConnectionError, match="Redis indisponível"):
        await redis_client.connect_redis()

    client.aclose.assert_awaited_once()
    assert redis_client._redis_client is None
