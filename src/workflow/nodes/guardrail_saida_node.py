from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage

from src.agents.base.base_prompt import build_system_prompt
from src.core.guardrails.anonymize import desanonimizar_texto
from src.core.guardrails.prompt import _PROMPT_COMPLIANCE
from src.core.llm.llm_groq import llm_groq
from src.workflow.state import Estado

PROMPT_GUARDRAIL_SAIDA = build_system_prompt(
    _PROMPT_COMPLIANCE, include_communication_standards=False
)


def no_guardrail_saida(estado: Estado) -> dict:
    ultima_msg_texto = estado["messages"][-1].content
    prompt_formatado = PROMPT_GUARDRAIL_SAIDA.format(resposta=ultima_msg_texto)
    resposta_revisada = (
        llm_groq().invoke([HumanMessage(content=prompt_formatado)]).content
    )

    resposta_final = resposta_revisada
    if "RESPOSTA:" in resposta_revisada.upper():
        resposta_final = resposta_revisada.split("RESPOSTA:", 1)[-1].strip()

    texto_final = desanonimizar_texto(resposta_final, estado["pii_map"])

    return {
        "messages": [
            RemoveMessage(id=estado["messages"][-1].id),
            AIMessage(content=texto_final),
        ],
        "agentes_chamados": ["guardrail_saida"],
    }
