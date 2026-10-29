import pytest

from src.core.config.settings import Settings


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in (
        "DB_MONGO_URI",
        "MONGO_URI",
        "MONGODB_URI",
        "DB_MONGO_AGENTS",
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


def test_agents_database_defaults_to_dbagents():
    assert Settings(_env_file=None).DB_MONGO_AGENTS == "dbagents"


def test_agents_database_reads_env(monkeypatch):
    monkeypatch.setenv("DB_MONGO_AGENTS", "dbagentsqa")

    assert Settings(_env_file=None).DB_MONGO_AGENTS == "dbagentsqa"
