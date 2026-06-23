import re
import uuid

PII_PADROES = [
    ("CPF", r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}"),
    ("EMAIL", r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
]

def anonimizar_texto(texto: str):
    mapa = {}
    for tipo, padrao in PII_PADROES:
        matches = re.findall(padrao, texto)
        for valor in matches:
            token = f"[PII_{tipo}_{uuid.uuid4().hex[:6]}]"
            mapa[token] = valor
            texto = texto.replace(valor, token, 1)
    return texto, mapa

def desanonimizar_texto(texto: str, mapa: dict) -> str:
    for token, valor in mapa.items():
        if token in texto:
            texto = texto.replace(token, f"[{token.split('_')[1]} OMITIDO]")
    return texto