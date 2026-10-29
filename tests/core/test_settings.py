import pytest

from src.core.config.settings import Settings


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in (
        "DB_MONGO_URI",
        "MONGO_URI",
        "MONGODB_URI",
        "UPSTASH_AGENTS_HOST",
        "UPSTASH_AGENTS_PORT",
        "UPSTASH_AGENTS_USERNAME",
        "UPSTASH_AGENTS_PASSWORD",
        "UPSTASH_REDIS_HOST",
    ):
        monkeypatch.delenv(name, raising=False)


def test_mongo_uri_reads_infisical_name(monkeypatch):
    monkeypatch.setenv("DB_MONGO_URI", "mongodb+srv://cluster.example.net")

    assert Settings(_env_file=None).MONGO_URI == "mongodb+srv://cluster.example.net"


def test_mongo_uri_adds_scheme_when_missing(monkeypatch):
    monkeypatch.setenv("DB_MONGO_URI", "cluster.example.net")

    assert Settings(_env_file=None).MONGO_URI == "mongodb+srv://cluster.example.net"


def test_mongo_uri_keeps_legacy_names(monkeypatch):
    monkeypatch.setenv("MONGODB_URI", "mongodb://legacy-host:27017")

    assert Settings(_env_file=None).MONGO_URI == "mongodb://legacy-host:27017"


def test_mongo_uri_defaults_to_localhost():
    assert Settings(_env_file=None).MONGO_URI == "mongodb://localhost:27017"


def test_redis_reads_infisical_names(monkeypatch):
    monkeypatch.setenv("UPSTASH_AGENTS_HOST", "agents.upstash.io")
    monkeypatch.setenv("UPSTASH_AGENTS_PORT", "6380")
    monkeypatch.setenv("UPSTASH_AGENTS_USERNAME", "agent")
    monkeypatch.setenv("UPSTASH_AGENTS_PASSWORD", "secret")

    settings = Settings(_env_file=None)

    assert settings.UPSTASH_REDIS_HOST == "agents.upstash.io"
    assert settings.UPSTASH_REDIS_PORT == 6380
    assert settings.UPSTASH_REDIS_USERNAME == "agent"
    assert settings.UPSTASH_REDIS_PASSWORD == "secret"
