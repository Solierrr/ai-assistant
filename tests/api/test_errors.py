from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver

from src.api.app import app

client = TestClient(app, raise_server_exceptions=False)


def _assert_problem(response, status, error_code, path):
    assert response.status_code == status
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["type"] == "about:blank"
    assert body["title"] == error_code
    assert body["status"] == status
    assert body["errorCode"] == error_code
    assert body["detail"]
    assert body["instance"] == path
    assert body["timestamp"]
    return body


def test_missing_token_is_unauthenticated_problem():
    response = client.post("/chat", json={"conversation_id": "c", "message": "oi"})

    _assert_problem(response, 401, "UNAUTHENTICATED", "/chat")


def test_invalid_body_is_validation_problem_with_fields():
    response = client.post("/chat", json={"conversation_id": "c", "message": ""})

    body = _assert_problem(response, 422, "VALIDATION_FAILED", "/chat")
    assert body["errors"] == [
        {
            "field": "message",
            "errorCode": "VALIDATION_FAILED",
            "detail": body["errors"][0]["detail"],
        }
    ]


def test_unknown_route_is_not_found_problem():
    response = client.get("/nao-existe")

    _assert_problem(response, 404, "NOT_FOUND", "/nao-existe")


def test_unexpected_error_is_internal_problem(monkeypatch):
    monkeypatch.setattr(
        "src.api.routes.chat.execute_turn",
        AsyncMock(side_effect=RuntimeError("segredo que não pode vazar")),
    )

    with patch(
        "src.memory.session.mongo_checkpointer.create_mongo_checkpointer",
        return_value=InMemorySaver(),
    ):
        response = client.post(
            "/chat",
            json={"conversation_id": "c", "message": "oi"},
            headers={"Authorization": "Bearer jwt"},
        )

    body = _assert_problem(response, 500, "INTERNAL_ERROR", "/chat")
    assert "segredo" not in body["detail"]
