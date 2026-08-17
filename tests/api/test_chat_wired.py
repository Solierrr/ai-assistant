from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver


@contextmanager
def _client():
    """TestClient com Mongo mockado — inclusive o checkpointer do grafo, que
    é construído na hora que `graph.py` é importado (dentro da rota)."""
    with (
        patch(
            "src.infra.database.mongo.mongodb_client.MongoDBClient.connect",
            new=AsyncMock(),
        ),
        patch("src.api.app.create_indexes", new=AsyncMock()),
        patch(
            "src.memory.session.mongo_checkpointer.create_mongo_checkpointer",
            return_value=InMemorySaver(),
        ),
    ):
        from src.api.app import app

        with TestClient(app) as client:
            yield client


def test_chat_calls_execute_turn_and_maps_response(monkeypatch):
    fake_message = AIMessage(
        content="Recomendo um instalador na região.",
        additional_kwargs={
            "specialists_used": ["professional_suggester"],
            "workflow_steps": ["router", "professional_suggester", "orchestrator"],
        },
    )
    fake_final_state = {"messages": [fake_message]}

    mock_execute_turn = AsyncMock(return_value=fake_final_state)
    monkeypatch.setattr("src.api.routes.chat.execute_turn", mock_execute_turn)

    with _client() as client:
        response = client.post(
            "/chat",
            json={"conversation_id": "conv-1", "message": "Preciso de instalador"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["response"] == "Recomendo um instalador na região."
    assert body["specialists_used"] == ["professional_suggester"]
    assert body["workflow_steps"] == [
        "router",
        "professional_suggester",
        "orchestrator",
    ]

    mock_execute_turn.assert_awaited_once()
    called_args = mock_execute_turn.call_args.args
    assert called_args[0] == "conv-1"
    assert called_args[1] == "Preciso de instalador"


def test_chat_falls_back_to_turn_agents_when_no_metadata(monkeypatch):
    fake_message = AIMessage(content="Resposta direta.", additional_kwargs={})
    fake_final_state = {
        "messages": [fake_message],
        "turn_agents": ["router_direct_response"],
    }

    mock_execute_turn = AsyncMock(return_value=fake_final_state)
    monkeypatch.setattr("src.api.routes.chat.execute_turn", mock_execute_turn)

    with _client() as client:
        response = client.post(
            "/chat", json={"conversation_id": "conv-2", "message": "Oi"}
        )

    body = response.json()
    assert body["specialists_used"] == []
    assert body["workflow_steps"] == ["router_direct_response"]


def test_app_import_does_not_touch_mongo_at_module_level():
    """O import de src.api.app não deve tentar conectar no Mongo sozinho."""
    import importlib

    import src.api.app as app_module

    importlib.reload(app_module)  # se travasse na conexão, o teste já teria estourado
    assert app_module.app is not None
