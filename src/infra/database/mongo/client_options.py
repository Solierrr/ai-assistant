from urllib.parse import parse_qs, urlsplit

import certifi


def mongo_uses_tls(uri: str) -> bool:
    if uri.lower().startswith("mongodb+srv://"):
        return True

    query = {
        key.lower(): values
        for key, values in parse_qs(urlsplit(uri).query).items()
    }
    tls_values = query.get("tls", []) + query.get("ssl", [])
    return any(value.lower() == "true" for value in tls_values)


def build_mongo_client_options(uri: str) -> dict[str, str]:
    if not mongo_uses_tls(uri):
        return {}
    return {"tlsCAFile": certifi.where()}
