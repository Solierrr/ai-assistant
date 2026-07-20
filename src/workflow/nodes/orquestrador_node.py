from langchain_core.messages import AIMessage, SystemMessage

from src.agents.base.base_prompt import build_system_prompt
from src.agents.specialist.orchestrator.orchestrator_prompt import ORCHESTRATOR_AGENT
from src.core.llm.llm_gemini import llm_gemini
from src.core.llm.llm_groq import llm_groq
from src.workflow.state import Estado

PROMPT_ORQUESTRADOR = build_system_prompt(ORCHESTRATOR_AGENT)


def no_orquestrador(estado: Estado) -> dict:
    mensagens_com_contexto = [SystemMessage(content=PROMPT_ORQUESTRADOR)] + estado[
        "messages"
    ]
    saida = (
        llm_gemini().with_fallbacks([llm_groq()]).invoke(mensagens_com_contexto).content
    )

    return {
        "messages": [AIMessage(content=saida)],
        "agentes_chamados": ["orquestrador"],
    }
