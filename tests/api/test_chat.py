import pytest
from fastapi.testclient import TestClient

from src.api.app import app

client = TestClient(app)


def test_chat_rejects_missing_fields():
    response = client.post("/chat", json={"batata": 1})

    assert response.status_code == 422


def test_chat_rejects_empty_message():
    response = client.post("/chat", json={"conversation_id": "conv-1", "message": ""})

    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"conversation_id": "   ", "message": "Olá"},
        {"conversation_id": "conv-1", "message": "   "},
    ],
)
def test_chat_rejects_fields_with_only_whitespace(payload):
    response = client.post("/chat", json=payload)

    assert response.status_code == 422
