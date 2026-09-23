from unittest.mock import AsyncMock
from uuid import UUID

import httpx
from fastapi.testclient import TestClient

from src.api.app import app
from src.workflow.runner import PreparedTurn

client = TestClient(app)
AUTH_HEADER = {"Authorization": "Bearer jwt-de-teste"}


def test_chat_prepara_turno_e_publica_sem_jwt(monkeypatch):
    prepared = PreparedTurn("conv-1", "messenger-1", "Preciso de instalador")
    prepare_turn = AsyncMock(return_value=prepared)
    publish_event = AsyncMock(return_value="1700000000000-0")
    monkeypatch.setattr("src.api.routes.chat.prepare_turn", prepare_turn)
    monkeypatch.setattr("src.api.routes.chat.publish_event", publish_event)

    response = client.post(
        "/chat",
        json={"conversation_id": "conv-1", "message": "Preciso de instalador"},
        headers=AUTH_HEADER,
    )

    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    UUID(response.json()["event_id"])
    prepare_turn.assert_awaited_once_with(
        "conv-1", "Preciso de instalador", "jwt-de-teste"
    )
    event = publish_event.await_args.args[0]
    assert event.payload == {
        "conversation_id": "conv-1",
        "messenger_conversation_id": "messenger-1",
        "message": "Preciso de instalador",
    }
    assert "jwt" not in str(event.to_stream_fields()).lower()


def test_chat_nao_publica_quando_api_messenger_rejeita(monkeypatch):
    request = httpx.Request("POST", "http://api-messenger/messaging/messages")
    response = httpx.Response(401, request=request)
    prepare_turn = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "unauthorized", request=request, response=response
        )
    )
    publish_event = AsyncMock()
    monkeypatch.setattr("src.api.routes.chat.prepare_turn", prepare_turn)
    monkeypatch.setattr("src.api.routes.chat.publish_event", publish_event)

    result = client.post(
        "/chat",
        json={"conversation_id": "conv-1", "message": "Oi"},
        headers=AUTH_HEADER,
    )

    assert result.status_code == 401
    publish_event.assert_not_awaited()


def test_chat_retorna_503_quando_redis_falha(monkeypatch):
    monkeypatch.setattr(
        "src.api.routes.chat.prepare_turn",
        AsyncMock(return_value=PreparedTurn("conv-1", "messenger-1", "Oi")),
    )
    monkeypatch.setattr(
        "src.api.routes.chat.publish_event",
        AsyncMock(side_effect=ConnectionError("Redis fora")),
    )

    response = client.post(
        "/chat",
        json={"conversation_id": "conv-1", "message": "Oi"},
        headers=AUTH_HEADER,
    )

    assert response.status_code == 503


def test_consultar_resultado_retorna_metricas(monkeypatch):
    event_id = "561373ea-20e2-45cb-864c-7e9e956f1bf2"
    monkeypatch.setattr(
        "src.api.routes.chat.get_event_result",
        AsyncMock(
            return_value={
                "event_id": event_id,
                "status": "completed",
                "conversation_id": "conv-1",
                "response": "Resposta",
                "queue_wait_ms": 12,
                "processing_time_ms": 1000,
                "total_time_ms": 1012,
            }
        ),
    )

    response = client.get(f"/chat/{event_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["total_time_ms"] == 1012


def test_consultar_resultado_404_quando_expirou(monkeypatch):
    monkeypatch.setattr(
        "src.api.routes.chat.get_event_result", AsyncMock(return_value=None)
    )

    response = client.get("/chat/561373ea-20e2-45cb-864c-7e9e956f1bf2")

    assert response.status_code == 404


def test_app_import_does_not_touch_mongo_at_module_level():
    assert app is not None
