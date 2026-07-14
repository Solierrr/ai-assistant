import asyncio
import importlib


def test_startup_connects_mongodb_and_creates_indexes(monkeypatch):
    main = importlib.import_module("main")
    calls = []

    async def fake_connect():
        calls.append("connect")

    async def fake_create_indexes():
        calls.append("create_indexes")

    monkeypatch.setattr(main.MongoDBClient, "connect", fake_connect)
    monkeypatch.setattr(main, "create_indexes", fake_create_indexes)

    asyncio.run(main.startup())

    assert calls == ["connect", "create_indexes"]
