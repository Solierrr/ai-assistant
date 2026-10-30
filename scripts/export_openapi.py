"""Grava em openapi.yaml o contrato gerado pelo FastAPI (make openapi). Não abre
banco nem lê segredo: só monta o app e pede o contrato."""

from pathlib import Path

import yaml

from src.api.app import app

ROOT = Path(__file__).resolve().parents[1]
VERSION_MARKER = " # x-release-please-version"


def main() -> None:
    schema = app.openapi()
    text = yaml.safe_dump(schema, sort_keys=False, allow_unicode=True)
    version_line = f"  version: {schema['info']['version']}\n"
    text = text.replace(
        version_line, version_line.rstrip("\n") + VERSION_MARKER + "\n", 1
    )
    (ROOT / "openapi.yaml").write_text(text, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
