from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage

from src.agents.base.base_prompt import build_system_prompt
from src.core.guardrails.anonymize import anonimizar_texto
from src.core.guardrails.prompt import _PROMPT_CLASSIFICADOR
from src.core.llm.llm_groq import llm_groq
from src.workflow.state import Estado

PROMPT_GUARDRAIL_ENTRADA = build_system_prompt(
    _PROMPT_CLASSIFICADOR, include_communication_standards=False
)


def no_guardrail_entrada(estado: Estado) -> dict:
    ultima_msg = estado["messages"][-1].content
    texto_anonimo, mapa_pii = anonimizar_texto(ultima_msg)
    prompt_formatado = PROMPT_GUARDRAIL_ENTRADA.format(mensagem=texto_anonimo)
    resposta = llm_groq().invoke([HumanMessage(content=prompt_formatado)]).content

    categoria = "INDEFINIDO"
    for linha in resposta.splitlines():
        if linha.upper().startswith("CATEGORIA:"):
            categoria = linha.split(":", 1)[1].strip().upper()
            break

    if categoria != "APROVADO":
        return {
            "messages": [
                RemoveMessage(id=estado["messages"][-1].id),
                AIMessage(
                    content="Desculpe, não posso processar essa solicitação por políticas de segurança."
                ),
            ],
            "rota": "fim",
            "pii_map": mapa_pii,
            "agentes_chamados": [f"guardrail_entrada_bloqueado_{categoria.lower()}"],
        }

    return {
        "messages": [
            RemoveMessage(id=estado["messages"][-1].id),
            HumanMessage(content=texto_anonimo),
        ],
        "rota": "prosseguir",
        "pii_map": mapa_pii,
        "agentes_chamados": ["guardrail_entrada_aprovado"],
    }
