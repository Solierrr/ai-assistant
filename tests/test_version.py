import json
from pathlib import Path

from src.version import VERSION


def test_version_matches_release_manifest():
    manifest = Path(__file__).resolve().parents[1] / ".release-please-manifest.json"

    assert VERSION == json.loads(manifest.read_text(encoding="utf-8"))["."]
