from src.core.config.settings import Settings


def test_settings_accepts_shared_mongo_environment_names(monkeypatch):
    monkeypatch.setenv("DB_MONGO_URI", "user:password@cluster.mongodb.net")
    monkeypatch.setenv("DB_MONGO_AGENTS", "solaria_agents")

    settings = Settings(_env_file=None)

    assert settings.MONGO_URI == "mongodb+srv://user:password@cluster.mongodb.net"
    assert settings.MONGO_DB == "solaria_agents"


def test_settings_preserves_complete_mongo_uri(monkeypatch):
    uri = "mongodb://localhost:27017"
    monkeypatch.setenv("DB_MONGO_URI", uri)

    settings = Settings(_env_file=None)

    assert settings.MONGO_URI == uri
