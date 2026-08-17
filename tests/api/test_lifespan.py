from unittest.mock import AsyncMock, patch


def test_lifespan_connects_mongo_and_creates_indexes():
    mock_connect = AsyncMock()
    mock_create_indexes = AsyncMock()

    with (
        patch(
            "src.infra.database.mongo.mongodb_client.MongoDBClient.connect",
            new=mock_connect,
        ),
        patch("src.api.app.create_indexes", new=mock_create_indexes),
    ):
        from fastapi.testclient import TestClient

        from src.api.app import app

        with TestClient(app):
            pass

    mock_connect.assert_awaited_once()
    mock_create_indexes.assert_awaited_once()
