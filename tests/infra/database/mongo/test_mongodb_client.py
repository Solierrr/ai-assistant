import asyncio
from unittest.mock import Mock

from src.infra.database import mongodb_sync_client
from src.infra.database.mongo import client_options
from src.infra.database.mongo import mongodb_client as mongodb_client_module
from src.memory.session import mongo_checkpointer


class FakeAsyncMongoClient:
    def __init__(self, uri, **options):
        self.uri = uri
        self.options = options
        self.databases = {}

    def __getitem__(self, database_name):
        database = {"name": database_name}
        self.databases[database_name] = database
        return database


def test_connect_creates_client_and_selects_database(monkeypatch):
    monkeypatch.setattr(
        mongodb_client_module,
        "AsyncMongoClient",
        FakeAsyncMongoClient
    )
    monkeypatch.setattr(
        mongodb_client_module.settings,
        "MONGO_URI",
        "mongodb://test-host:27017"
    )
    monkeypatch.setattr(
        mongodb_client_module.settings,
        "MONGO_DB",
        "test_database"
    )

    asyncio.run(mongodb_client_module.MongoDBClient.connect())

    assert mongodb_client_module.MongoDBClient.client.uri == (
        "mongodb://test-host:27017"
    )
    assert mongodb_client_module.MongoDBClient.database == {
        "name": "test_database"
    }
    assert mongodb_client_module.MongoDBClient.client.options == {}


def test_get_database_returns_current_database():
    database = object()
    mongodb_client_module.MongoDBClient.database = database

    assert mongodb_client_module.MongoDBClient.get_database() is database


def test_sync_client_uses_configured_mongo_uri(monkeypatch):
    client = object()
    mongo_client = Mock(return_value=client)
    monkeypatch.setattr(mongodb_sync_client, "MongoClient", mongo_client)
    monkeypatch.setattr(
        mongodb_sync_client.settings,
        "MONGO_URI",
        "mongodb://configured-host:27017",
    )

    result = mongodb_sync_client.get_mongodb_client()

    assert result is client
    mongo_client.assert_called_once_with("mongodb://configured-host:27017")


def test_async_client_uses_certifi_for_atlas(monkeypatch):
    monkeypatch.setattr(
        mongodb_client_module,
        "AsyncMongoClient",
        FakeAsyncMongoClient,
    )
    monkeypatch.setattr(
        mongodb_client_module.settings,
        "MONGO_URI",
        "mongodb+srv://user:password@cluster.mongodb.net/database",
    )
    monkeypatch.setattr(
        mongodb_client_module.settings,
        "MONGO_DB",
        "test_database",
    )
    monkeypatch.setattr(
        client_options.certifi,
        "where",
        Mock(return_value="ca-bundle.pem"),
    )

    asyncio.run(mongodb_client_module.MongoDBClient.connect())

    assert mongodb_client_module.MongoDBClient.client.options == {
        "tlsCAFile": "ca-bundle.pem"
    }


def test_sync_client_uses_certifi_when_tls_is_enabled(monkeypatch):
    mongo_client = Mock()
    monkeypatch.setattr(mongodb_sync_client, "MongoClient", mongo_client)
    monkeypatch.setattr(
        mongodb_sync_client.settings,
        "MONGO_URI",
        "mongodb://cluster.mongodb.net/database?tls=true",
    )
    monkeypatch.setattr(
        client_options.certifi,
        "where",
        Mock(return_value="ca-bundle.pem"),
    )

    mongodb_sync_client.get_mongodb_client()

    mongo_client.assert_called_once_with(
        "mongodb://cluster.mongodb.net/database?tls=true",
        tlsCAFile="ca-bundle.pem",
    )


def test_client_options_preserve_local_connection_without_tls():
    options = client_options.build_mongo_client_options(
        "mongodb://localhost:27017"
    )

    assert options == {}


def test_checkpointer_uses_configured_database(monkeypatch):
    client = object()
    saver = object()
    mongo_saver = Mock(return_value=saver)
    monkeypatch.setattr(
        mongo_checkpointer,
        "get_mongodb_client",
        Mock(return_value=client),
    )
    monkeypatch.setattr(mongo_checkpointer, "MongoDBSaver", mongo_saver)
    monkeypatch.setattr(
        mongo_checkpointer.settings,
        "MONGO_DB",
        "configured_database",
    )

    result = mongo_checkpointer.create_mongo_checkpointer()

    assert result is saver
    mongo_saver.assert_called_once_with(
        client=client,
        db_name="configured_database",
        collection_name="checkpoints_conversas",
    )
