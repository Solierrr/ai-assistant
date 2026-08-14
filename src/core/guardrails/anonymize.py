import re
import uuid

# CNPJ vem antes do CPF: um CNPJ sem formatação (14 dígitos) contém um
# prefixo de 11 dígitos que bateria com o padrão de CPF se fosse processado
# primeiro. Processar CNPJ primeiro tokeniza esses dígitos antes que o
# padrão de CPF rode sobre o texto.
PII_PATTERNS = [
    ("CNPJ", r"\b\d{2}\.?\d{3}\.?\d{3}\/?\d{4}-?\d{2}\b"),
    ("CPF", r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"),
    ("TELEFONE", r"\b\(?\d{2}\)?[\s-]?9?\d{4}-?\d{4}\b"),
    ("EMAIL", r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
]


def anonymize_text(text: str) -> tuple[str, dict]:
    """Substitui CNPJ, CPF, telefone e email por tokens únicos. A mesma
    ocorrência de um valor (ex: o mesmo CPF citado duas vezes na mensagem)
    sempre recebe o mesmo token, para não gerar mapeamentos duplicados nem
    tokens diferentes para o mesmo dado."""
    pii_map = {}
    token_by_value = {}

    for pii_type, pattern in PII_PATTERNS:
        for value in set(re.findall(pattern, text)):
            token = token_by_value.get(value)
            if token is None:
                token = f"[PII_{pii_type}_{uuid.uuid4().hex[:6]}]"
                token_by_value[value] = token
                pii_map[token] = value
            text = re.sub(re.escape(value), token, text)

    return text, pii_map


def deanonymize_text(text: str, pii_map: dict) -> str:
    for token, value in pii_map.items():
        if token in text:
            text = text.replace(token, f"[{token.split('_')[1]} OMITIDO]")
    return text
