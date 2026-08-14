import re

# Padrões óbvios de tentativa de manipulação (prompt injection / jailbreak).
_MANIPULATION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"ignor[ae]\w*\s+(as\s+)?(instru[çc][õo]es|regras|comandos)",
        r"esque[çc]a\s+(tudo|suas\s+instru[çc][õo]es)",
        r"voc[êe]\s+agora\s+[ée]",
        r"a\s+partir\s+de\s+agora\s+voc[êe]",
        r"finja\s+(que|ser)",
        r"modo\s+(irrestrito|sem\s+filtro|desbloqueado|developer|dev)",
        r"you\s+are\s+now",
        r"ignore\s+(all\s+|previous\s+|above\s+)*instructions",
        r"disregard\s+(all\s+)?(previous|prior)\s+instructions",
        r"\[inst\]",
        r"(ignore|disregard|forget)\s+(your\s+|the\s+)?system\s+prompt",
    ]
]

# Padrões de tentativa de acessar dados/infraestrutura internos da plataforma.
_INTERNAL_DATA_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"(mostre|revele|qual\s+[ée]).{0,25}?(system\s+)?prompt",
        r"su(as|a)\s+instru[çc][õo]es\s+(internas|originais|completas)",
        r"c[óo]digo[- ]fonte",
        r"vari[áa]veis?\s+de\s+ambiente",
        r"api[_\s-]?key",
        r"chave\s+de\s+api",
        r"credenciais",
    ]
]


def pre_filter_category(text: str) -> str | None:
    """Checa padrões óbvios de prompt injection e de acesso a dados internos
    antes de gastar uma chamada de LLM. Retorna a mesma categoria usada pelo
    classificador (MANIPULACAO ou DADOS_INTERNOS) quando um padrão bate, ou
    None se nada bater — nesse caso a decisão fica por conta da LLM.

    É uma camada barata e determinística: pega ataques óbvios mesmo se a LLM
    falhar em classificar corretamente, sem substituir o classificador."""
    for pattern in _MANIPULATION_PATTERNS:
        if pattern.search(text):
            return "MANIPULACAO"

    for pattern in _INTERNAL_DATA_PATTERNS:
        if pattern.search(text):
            return "DADOS_INTERNOS"

    return None
