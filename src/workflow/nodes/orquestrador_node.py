from src.workflow.state import Estado
from langchain_core.messages import SystemMessage, AIMessage
from src.core.llm.llm_gemini import llm_gemini
from src.core.llm.llm_groq import llm_groq

PROMPT_ORQUESTRADOR = """

"""


def no_orquestrador(estado: Estado) -> dict:

    prompt_sistema = PROMPT_ORQUESTRADOR.format(rota=estado["rota"])

    mensagens_com_contexto = [SystemMessage(content=prompt_sistema)] + estado[
        "messages"
    ]
    saida = (
        llm_gemini().with_fallbacks([llm_groq()]).invoke(mensagens_com_contexto).content
    )

    return {
        "messages": [AIMessage(content=saida)],
        "agentes_chamados": ["orquestrador"],
    }
