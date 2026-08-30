from unittest.mock import AsyncMock, patch

import pytest


def test_lifespan_connects_dependencies_and_manages_consumers():
    mock_connect = AsyncMock()
    mock_create_indexes = AsyncMock()
    mock_connect_redis = AsyncMock()
    mock_ensure_consumer_group = AsyncMock()
    mock_run_consumer = AsyncMock()
    mock_close_redis = AsyncMock()

    with (
        patch(
            "src.infra.database.mongo.mongodb_client.MongoDBClient.connect",
            new=mock_connect,
        ),
        patch("src.api.app.create_indexes", new=mock_create_indexes),
        patch("src.api.app.connect_redis", new=mock_connect_redis),
        patch(
            "src.api.app.ensure_consumer_group",
            new=mock_ensure_consumer_group,
        ),
        patch("src.api.app.run_consumer", new=mock_run_consumer),
        patch("src.api.app.close_redis", new=mock_close_redis),
        patch("src.api.app.settings.AGENT_CONSUMER_COUNT", 2),
    ):
        from fastapi.testclient import TestClient

        from src.api.app import app

        with TestClient(app):
            pass

    mock_connect.assert_awaited_once()
    mock_create_indexes.assert_awaited_once()
    mock_connect_redis.assert_awaited_once()
    mock_ensure_consumer_group.assert_awaited_once()
    assert mock_run_consumer.await_count == 2
    mock_close_redis.assert_awaited_once()


def test_lifespan_closes_redis_when_group_setup_fails():
    mock_close_redis = AsyncMock()

    with (
        patch(
            "src.infra.database.mongo.mongodb_client.MongoDBClient.connect",
            new=AsyncMock(),
        ),
        patch("src.api.app.create_indexes", new=AsyncMock()),
        patch("src.api.app.connect_redis", new=AsyncMock()),
        patch(
            "src.api.app.ensure_consumer_group",
            new=AsyncMock(side_effect=ConnectionError("Redis indisponível")),
        ),
        patch("src.api.app.close_redis", new=mock_close_redis),
    ):
        from fastapi.testclient import TestClient

        from src.api.app import app

        with pytest.raises(ConnectionError, match="Redis indisponível"), TestClient(app):
            pass

    mock_close_redis.assert_awaited_once()
