import asyncio

from src.infra.database.mongo.repositories import (
    conversation_repository as conversation_repository_module,
)
from src.infra.database.mongo.repositories import (
    message_repository as message_repository_module,
)


class FakeInsertResult:
    inserted_id = "inserted-id"


class FakeUpdateResult:
    modified_count = 1


class FakeCursor:
    def __init__(self, messages):
        self.messages = messages
        self.sort_args = None

    def sort(self, field, direction):
        self.sort_args = (field, direction)
        return self

    async def to_list(self, length):
        return self.messages[:length]


class FakeCollection:
    def __init__(self, messages=None):
        self.inserted = []
        self.find_one_query = None
        self.update_one_args = None
        self.find_query = None
        self.cursor = FakeCursor(messages or [])

    async def insert_one(self, data):
        self.inserted.append(data)
        return FakeInsertResult()

    async def find_one(self, query):
        self.find_one_query = query
        return {"conversation_id": query["conversation_id"]}

    async def update_one(self, query, update):
        self.update_one_args = (query, update)
        return FakeUpdateResult()

    def find(self, query):
        self.find_query = query
        return self.cursor


class FakeDatabase:
    def __init__(self):
        self.collections = {
            "conversations": FakeCollection(),
            "messages": FakeCollection([
                {"content": "primeira"},
                {"content": "segunda"},
            ]),
        }

    def __getitem__(self, collection_name):
        return self.collections[collection_name]


def test_conversation_repository_creates_conversation(monkeypatch):
    db = FakeDatabase()
    monkeypatch.setattr(
        conversation_repository_module.MongoDBClient,
        "get_database",
        lambda: db
    )
    repository = conversation_repository_module.ConversationRepository()
    data = {"conversation_id": "conv-1"}

    result = asyncio.run(repository.create(data))

    assert result.inserted_id == "inserted-id"
    assert db.collections["conversations"].inserted == [data]


def test_conversation_repository_finds_by_conversation_id(monkeypatch):
    db = FakeDatabase()
    monkeypatch.setattr(
        conversation_repository_module.MongoDBClient,
        "get_database",
        lambda: db
    )
    repository = conversation_repository_module.ConversationRepository()

    result = asyncio.run(repository.find_by_id("conv-1"))

    assert result == {"conversation_id": "conv-1"}
    assert db.collections["conversations"].find_one_query == {
        "conversation_id": "conv-1"
    }


def test_conversation_repository_updates_active_agent(monkeypatch):
    db = FakeDatabase()
    monkeypatch.setattr(
        conversation_repository_module.MongoDBClient,
        "get_database",
        lambda: db
    )
    repository = conversation_repository_module.ConversationRepository()

    result = asyncio.run(
        repository.update_active_agent("conv-1", "faq_reader")
    )

    assert result.modified_count == 1
    assert db.collections["conversations"].update_one_args == (
        {"conversation_id": "conv-1"},
        {"$set": {"active_agent": "faq_reader"}},
    )


def test_message_repository_saves_message(monkeypatch):
    db = FakeDatabase()
    monkeypatch.setattr(
        message_repository_module.MongoDBClient,
        "get_database",
        lambda: db
    )
    repository = message_repository_module.MessageRepository()
    data = {"conversation_id": "conv-1", "content": "ola"}

    result = asyncio.run(repository.save_message(data))

    assert result.inserted_id == "inserted-id"
    assert db.collections["messages"].inserted == [data]


def test_message_repository_gets_messages_sorted_by_timestamp(monkeypatch):
    db = FakeDatabase()
    monkeypatch.setattr(
        message_repository_module.MongoDBClient,
        "get_database",
        lambda: db
    )
    repository = message_repository_module.MessageRepository()

    messages = asyncio.run(
        repository.get_messages_by_conversation("conv-1")
    )

    message_collection = db.collections["messages"]
    assert messages == [
        {"content": "primeira"},
        {"content": "segunda"},
    ]
    assert message_collection.find_query == {"conversation_id": "conv-1"}
    assert message_collection.cursor.sort_args == ("timestamp", 1)
