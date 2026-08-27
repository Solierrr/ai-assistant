from src.infra.database import mongodb_sync_client


def test_get_mongodb_client_usa_uri_das_settings(monkeypatch):
    criados = []
    monkeypatch.setattr(mongodb_sync_client, "MongoClient", criados.append)
    monkeypatch.setattr(
        mongodb_sync_client.settings, "MONGO_URI", "mongodb://test-host:27017"
    )

    mongodb_sync_client.get_mongodb_client()

    assert criados == ["mongodb://test-host:27017"]
