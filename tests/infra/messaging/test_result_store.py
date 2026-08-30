import json
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest

from src.infra.messaging import result_store


def test_build_result_key_combina_prefixo_e_event_id():
    event_id = UUID("550e8400-e29b-41d4-a716-446655440000")

    key = result_store.build_result_key(event_id)

    assert key == f"{result_store.settings.AGENT_RESULT_PREFIX}:{event_id}"


async def test_save_event_result_salva_json_com_ttl(monkeypatch):
    redis = Mock()
    redis.set = AsyncMock(return_value=True)
    monkeypatch.setattr(result_store, "get_redis_client", Mock(return_value=redis))
    event_id = UUID("550e8400-e29b-41d4-a716-446655440000")

    await result_store.save_event_result(
        event_id,
        {
            "status": "queued",
            "message": "Pergunta recebida",
            "event_id": "valor-incorreto",
        },
    )

    redis.set.assert_awaited_once()
    call = redis.set.await_args.kwargs
    assert call["name"] == result_store.build_result_key(event_id)
    assert call["ex"] == result_store.settings.AGENT_RESULT_TTL_SECONDS
    assert json.loads(call["value"]) == {
        "status": "queued",
        "message": "Pergunta recebida",
        "event_id": str(event_id),
    }


async def test_save_event_result_preserva_caracteres_unicode(monkeypatch):
    redis = Mock()
    redis.set = AsyncMock(return_value=True)
    monkeypatch.setattr(result_store, "get_redis_client", Mock(return_value=redis))

    await result_store.save_event_result(
        "event-123",
        {"status": "completed", "response": "Olá, instalação concluída"},
    )

    stored_json = redis.set.await_args.kwargs["value"]
    assert "Olá, instalação concluída" in stored_json


async def test_get_event_result_retorna_resultado_existente(monkeypatch):
    redis = Mock()
    redis.get = AsyncMock(
        return_value=json.dumps(
            {
                "event_id": "event-123",
                "status": "completed",
                "response": "Resposta final",
            }
        )
    )
    monkeypatch.setattr(result_store, "get_redis_client", Mock(return_value=redis))

    result = await result_store.get_event_result("event-123")

    assert result == {
        "event_id": "event-123",
        "status": "completed",
        "response": "Resposta final",
    }
    redis.get.assert_awaited_once_with(result_store.build_result_key("event-123"))


async def test_get_event_result_retorna_none_quando_chave_nao_existe(monkeypatch):
    redis = Mock()
    redis.get = AsyncMock(return_value=None)
    monkeypatch.setattr(result_store, "get_redis_client", Mock(return_value=redis))

    result = await result_store.get_event_result("event-inexistente")

    assert result is None


async def test_get_event_result_propaga_json_invalido(monkeypatch):
    redis = Mock()
    redis.get = AsyncMock(return_value="{json-invalido")
    monkeypatch.setattr(result_store, "get_redis_client", Mock(return_value=redis))

    with pytest.raises(json.JSONDecodeError):
        await result_store.get_event_result("event-123")


async def test_delete_event_result_remove_chave_correta(monkeypatch):
    redis = Mock()
    redis.delete = AsyncMock(return_value=1)
    monkeypatch.setattr(result_store, "get_redis_client", Mock(return_value=redis))

    await result_store.delete_event_result("event-123")

    redis.delete.assert_awaited_once_with(result_store.build_result_key("event-123"))


async def test_save_event_result_propaga_falha_do_redis(monkeypatch):
    redis = Mock()
    redis.set = AsyncMock(side_effect=ConnectionError("Redis indisponivel"))
    monkeypatch.setattr(result_store, "get_redis_client", Mock(return_value=redis))

    with pytest.raises(ConnectionError, match="Redis indisponivel"):
        await result_store.save_event_result("event-123", {"status": "queued"})
