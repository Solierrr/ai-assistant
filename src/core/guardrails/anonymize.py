import re
import uuid

PII_PATTERNS = [
    ("CNPJ", r"(?<!\d)\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}(?!\d)"),
    ("CPF", r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)"),
    ("TELEFONE", r"(?<!\d)(?:\+55\s?)?\(?\d{2}\)?[\s-]?9\d{4}-\d{4}(?!\d)"),
    ("EMAIL", r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
]


def anonymize_text(text: str):
    pii_map = {}
    for pii_type, pattern in PII_PATTERNS:
        matches = set(re.findall(pattern, text))
        for value in matches:
            token = f"[PII_{pii_type}_{uuid.uuid4().hex}]"
            pii_map[token] = value
            text = text.replace(value, token)
    return text, pii_map


def deanonymize_text(text: str, pii_map: dict) -> str:
    for token, value in pii_map.items():
        if token in text:
            text = text.replace(token, value)
    return text


def redact_unmapped_pii(text: str, pii_map: dict) -> str:
    """Keep known session tokens and redact other PII before persistence."""
    known_values = {value: token for token, value in pii_map.items()}
    for pii_type, pattern in PII_PATTERNS:
        def replace(match: re.Match[str]) -> str:
            value = match.group(0)
            return known_values.get(value, f"[{pii_type} OMITIDO]")

        text = re.sub(pattern, replace, text)
    return text


def redact_unresolved_pii_tokens(text: str, pii_map: dict) -> str:
    known_tokens = set(pii_map)
    token_pattern = re.compile(r"\[PII_(CNPJ|CPF|TELEFONE|EMAIL)_[0-9a-f]{6,32}\]")
    return token_pattern.sub(
        lambda match: match.group(0)
        if match.group(0) in known_tokens
        else f"[{match.group(1)} OMITIDO]",
        text,
    )
