from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from src.api.app import app
from src.version import VERSION

client = TestClient(app)


def test_contract_follows_the_standard():
    contract = client.get("/openapi.json").json()

    assert contract["info"]["title"] == "Solaria — ai-assistant"
    assert contract["info"]["version"] == VERSION
    assert contract["info"]["license"]["name"] == "CC0-1.0"
    assert contract["servers"][0]["description"] == "QA"
    assert contract["security"] == [{"bearerAuth": []}]
    assert contract["components"]["securitySchemes"]["bearerAuth"] == {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    assert set(contract["paths"]) == {"/chat", "/health", "/ready"}
    assert "ProblemDetail" in contract["components"]["schemas"]
    assert "HTTPValidationError" not in contract["components"]["schemas"]


def test_every_error_response_is_problem_detail():
    contract = client.get("/openapi.json").json()

    for path in contract["paths"].values():
        for operation in path.values():
            assert "500" in operation["responses"]
            for code, response in operation["responses"].items():
                if code.startswith(("4", "5")):
                    assert list(response["content"]) == ["application/problem+json"]


def test_health_routes_are_public():
    contract = client.get("/openapi.json").json()

    assert contract["paths"]["/health"]["get"]["security"] == []
    assert contract["paths"]["/ready"]["get"]["security"] == []


def test_exported_contract_carries_the_release_marker():
    exported = Path(__file__).resolve().parents[2] / "openapi.yaml"
    text = exported.read_text(encoding="utf-8")

    assert f"  version: {VERSION} # x-release-please-version\n" in text
    assert yaml.safe_load(text)["info"]["version"] == VERSION
