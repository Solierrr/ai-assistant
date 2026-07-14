from src.workflow.state import Estado
from langchain_core.messages import RemoveMessage, HumanMessage, AIMessage
from src.core.llm.llm_groq import llm_groq
from src.core.guardrails.anonymize import desanonimizar_texto

PROMPT_GUARDRAIL_SAIDA = """

"""


def no_guardrail_saida(estado: Estado) -> dict:
    ultima_msg_texto = estado["messages"][-1].content

    # 1. Compliance / Revisão semântica da saída
    prompt_formatado = PROMPT_GUARDRAIL_SAIDA.format(resposta=ultima_msg_texto)
    resposta_revisada = (
        llm_groq().invoke([HumanMessage(content=prompt_formatado)]).content
    )

    # 2. Desanonimização antes de entregar ao usuário final
    texto_final = desanonimizar_texto(resposta_revisada, estado["pii_map"])

    return {
        "messages": [
            RemoveMessage(id=estado["messages"][-1].id),
            AIMessage(content=texto_final),
        ],
        "agentes_chamados": ["guardrail_saida"],
    }
