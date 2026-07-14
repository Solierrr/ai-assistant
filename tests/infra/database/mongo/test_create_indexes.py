import asyncio

from src.infra.database.mongo.indexes import create_indexes as create_indexes_module


class FakeCollection:
    def __init__(self):
        self.created_indexes = []

    async def create_index(self, field, **kwargs):
        self.created_indexes.append((field, kwargs))


class FakeDatabase:
    def __init__(self):
        self.conversations = FakeCollection()
        self.messages = FakeCollection()


def test_create_indexes_creates_expected_indexes(monkeypatch):
    db = FakeDatabase()
    monkeypatch.setattr(
        create_indexes_module.MongoDBClient,
        "get_database",
        lambda: db
    )

    asyncio.run(create_indexes_module.create_indexes())

    assert db.conversations.created_indexes == [
        ("conversation_id", {"unique": True})
    ]
    assert db.messages.created_indexes == [
        ("conversation_id", {}),
        ("timestamp", {})
    ]
