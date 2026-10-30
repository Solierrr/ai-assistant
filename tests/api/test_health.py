from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from src.api.app import app
from src.version import VERSION

client = TestClient(app)


def test_health_returns_up_with_version():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "UP", "version": VERSION}


def test_ready_returns_up_when_mongo_answers(monkeypatch):
    monkeypatch.setattr("src.api.routes.health.ping_mongo", AsyncMock())

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "UP"}


def test_ready_returns_503_when_mongo_fails(monkeypatch):
    monkeypatch.setattr(
        "src.api.routes.health.ping_mongo",
        AsyncMock(side_effect=ConnectionError("mongo fora")),
    )

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "DOWN"}


def test_ready_returns_503_when_mongo_times_out(monkeypatch):
    async def slow_ping():
        import asyncio

        await asyncio.sleep(1)

    monkeypatch.setattr("src.api.routes.health.READY_TIMEOUT_SECONDS", 0.01)
    monkeypatch.setattr("src.api.routes.health.ping_mongo", slow_ping)

    response = client.get("/ready")

    assert response.status_code == 503
