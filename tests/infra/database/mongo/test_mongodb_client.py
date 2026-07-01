import asyncio

from src.infra.database.mongo import mongodb_client as mongodb_client_module


class FakeAsyncIOMotorClient:
    def __init__(self, uri):
        self.uri = uri
        self.databases = {}

    def __getitem__(self, database_name):
        database = {"name": database_name}
        self.databases[database_name] = database
        return database


def test_connect_creates_client_and_selects_database(monkeypatch):
    monkeypatch.setattr(
        mongodb_client_module,
        "AsyncIOMotorClient",
        FakeAsyncIOMotorClient
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


def test_get_database_returns_current_database():
    database = object()
    mongodb_client_module.MongoDBClient.database = database

    assert mongodb_client_module.MongoDBClient.get_database() is database
