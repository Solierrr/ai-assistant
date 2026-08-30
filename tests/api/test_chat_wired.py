from contextlib import contextmanager
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient


@contextmanager
def _client():
    """Cria um cliente da API sem acessar o MongoDB real."""
    with (
        patch(
            "src.infra.database.mongo.mongodb_client.MongoDBClient.connect",
            new=AsyncMock(),
        ),
        patch("src.api.app.create_indexes", new=AsyncMock()),
        patch("src.api.app.connect_redis", new=AsyncMock()),
        patch("src.api.app.ensure_consumer_group", new=AsyncMock()),
        patch("src.api.app.run_consumer", new=AsyncMock()),
        patch("src.api.app.close_redis", new=AsyncMock()),
    ):
        from src.api.app import app

        with TestClient(app) as client:
            yield client


def test_chat_publica_evento_e_retorna_accepted(monkeypatch):
    save_event_result = AsyncMock()
    publish_event = AsyncMock(return_value="1700000000000-0")
    delete_event_result = AsyncMock()
    monkeypatch.setattr(
        "src.api.routes.chat.save_event_result",
        save_event_result,
    )
    monkeypatch.setattr("src.api.routes.chat.publish_event", publish_event)
    monkeypatch.setattr(
        "src.api.routes.chat.delete_event_result",
        delete_event_result,
    )

    with _client() as client:
        response = client.post(
            "/chat",
            json={"conversation_id": "conv-1", "message": "Preciso de instalador"},
        )

    assert response.status_code == 202
    body = response.json()
    event_id = UUID(body["event_id"])
    assert body["status"] == "queued"
    saved_event_id, saved_result = save_event_result.await_args.args
    assert saved_event_id == event_id
    assert saved_result == {
        "status": "queued",
        "conversation_id": "conv-1",
    }
    published_event = publish_event.await_args.args[0]
    assert published_event.event_id == event_id
    assert published_event.event_type == "chatbot.message.received"
    assert published_event.payload == {
        "conversation_id": "conv-1",
        "message": "Preciso de instalador",
    }
    delete_event_result.assert_not_awaited()


def test_chat_remove_resultado_temporario_quando_publicacao_falha(monkeypatch):
    save_event_result = AsyncMock()
    publish_event = AsyncMock(side_effect=ConnectionError("Redis indisponível"))
    delete_event_result = AsyncMock()
    monkeypatch.setattr(
        "src.api.routes.chat.save_event_result",
        save_event_result,
    )
    monkeypatch.setattr("src.api.routes.chat.publish_event", publish_event)
    monkeypatch.setattr(
        "src.api.routes.chat.delete_event_result",
        delete_event_result,
    )

    with pytest.raises(ConnectionError, match="Redis indisponível"), _client() as client:
        client.post(
            "/chat",
            json={"conversation_id": "conv-1", "message": "Olá"},
        )

    event_id = save_event_result.await_args.args[0]
    delete_event_result.assert_awaited_once_with(event_id)


def test_chat_retorna_resultado_concluido(monkeypatch):
    event_id = UUID("550e8400-e29b-41d4-a716-446655440000")
    get_event_result = AsyncMock(
        return_value={
            "event_id": str(event_id),
            "status": "completed",
            "conversation_id": "conv-1",
            "response": "Resposta final",
            "specialists_used": ["faq_reader"],
            "workflow_steps": ["router", "faq_reader", "orchestrator"],
        }
    )
    monkeypatch.setattr(
        "src.api.routes.chat.get_event_result",
        get_event_result,
    )

    with _client() as client:
        response = client.get(f"/chat/{event_id}")

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "event_id": str(event_id),
        "status": "completed",
        "conversation_id": "conv-1",
        "response": "Resposta final",
        "specialists_used": ["faq_reader"],
        "workflow_steps": ["router", "faq_reader", "orchestrator"],
    }
    get_event_result.assert_awaited_once_with(event_id)


def test_chat_retorna_404_quando_evento_nao_existe(monkeypatch):
    event_id = UUID("550e8400-e29b-41d4-a716-446655440000")
    monkeypatch.setattr(
        "src.api.routes.chat.get_event_result",
        AsyncMock(return_value=None),
    )

    with _client() as client:
        response = client.get(f"/chat/{event_id}")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Evento não encontrado ou expirado."
    }


def test_chat_routes_expose_descriptions_in_openapi():
    with _client() as client:
        openapi = client.get("/openapi.json").json()

    post_operation = openapi["paths"]["/chat"]["post"]
    get_operation = openapi["paths"]["/chat/{event_id}"]["get"]
    assert post_operation["summary"] == "Enviar mensagem ao chatbot"
    assert "Enfileira uma mensagem" in post_operation["description"]
    assert get_operation["summary"] == "Consultar processamento do chatbot"
    assert "resultado temporário" in get_operation["description"]


def test_app_import_does_not_touch_mongo_at_module_level():
    """O import de src.api.app não deve tentar conectar no Mongo sozinho."""
    import importlib

    import src.api.app as app_module

    importlib.reload(app_module)  # se travasse na conexão, o teste já teria estourado
    assert app_module.app is not None
