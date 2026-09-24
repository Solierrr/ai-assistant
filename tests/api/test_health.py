from fastapi.testclient import TestClient

from src.api.app import app

client = TestClient(app)


def test_health_returns_ok_when_settings_present(monkeypatch):
    monkeypatch.setattr("src.api.app.settings.GOOGLE_API_KEY", "fake-key")
    monkeypatch.setattr("src.api.app.settings.GROQ_API_KEY", "fake-key")
    monkeypatch.setattr("src.api.app.settings.UPSTASH_AGENTS_HOST", "redis.test")
    monkeypatch.setattr("src.api.app.settings.UPSTASH_AGENTS_PASSWORD", "secret")
    monkeypatch.setattr("src.api.app.settings.UPSTASH_CORE_HOST", "core.test")
    monkeypatch.setattr("src.api.app.settings.UPSTASH_CORE_PASSWORD", "secret")
    monkeypatch.setattr("src.api.app.settings.PII_ENCRYPTION_KEY", "key")

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "missing_settings": []}


def test_health_reports_missing_settings(monkeypatch):
    monkeypatch.setattr("src.api.app.settings.GOOGLE_API_KEY", None)
    monkeypatch.setattr("src.api.app.settings.GROQ_API_KEY", None)
    monkeypatch.setattr("src.api.app.settings.UPSTASH_AGENTS_HOST", None)
    monkeypatch.setattr("src.api.app.settings.UPSTASH_AGENTS_PASSWORD", None)
    monkeypatch.setattr("src.api.app.settings.UPSTASH_CORE_HOST", None)
    monkeypatch.setattr("src.api.app.settings.UPSTASH_CORE_PASSWORD", None)
    monkeypatch.setattr("src.api.app.settings.PII_ENCRYPTION_KEY", None)

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "atencao"
    assert "GOOGLE_API_KEY" in body["missing_settings"]
    assert "GROQ_API_KEY" in body["missing_settings"]
    assert "UPSTASH_AGENTS_HOST" in body["missing_settings"]
    assert "UPSTASH_AGENTS_PASSWORD" in body["missing_settings"]
    assert "UPSTASH_CORE_HOST" in body["missing_settings"]
    assert "UPSTASH_CORE_PASSWORD" in body["missing_settings"]
    assert "PII_ENCRYPTION_KEY" in body["missing_settings"]
