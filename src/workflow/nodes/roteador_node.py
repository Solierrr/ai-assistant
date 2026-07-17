from langchain_core.messages import AIMessage, SystemMessage

from src.agents.base.base_prompt import build_system_prompt
from src.agents.specialist.router.router_prompt import ROUTER_AGENT
from src.core.llm.llm_groq import llm_groq
from src.workflow.state import Estado

PROMPT_ROTEADOR = build_system_prompt(ROUTER_AGENT)


def no_roteador(estado: Estado) -> dict:
    mensagens_com_contexto = [SystemMessage(content=PROMPT_ROTEADOR)] + estado[
        "messages"
    ]
    saida = llm_groq().invoke(mensagens_com_contexto).content

    if "ROUTE=" in saida:
        rota_extraida = saida.split("ROUTE=")[1].strip().splitlines()[0]
        return {"rota": rota_extraida, "agentes_chamados": ["roteador"]}

    return {
        "messages": [AIMessage(content=saida)],
        "rota": "fim",
        "agentes_chamados": ["roteador_resposta_direta"],
    }
