from src.workflow.state import Estado
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from src.core.llm.llm_groq import llm_groq

PROMPT_ROTEADOR = """

"""

def no_roteador(estado: Estado) -> dict:
    mensagens_com_contexto = [SystemMessage(content=PROMPT_ROTEADOR)] + estado["messages"]
    saida = llm_groq().invoke(mensagens_com_contexto).content
    
    if "ROUTE=" in saida:
        # Extrai a rota dinâmica (ex: ROUTE=financeiro)
        rota_extraida = saida.split("ROUTE=")[1].strip().splitlines()[0]
        return {
            "rota": rota_extraida,
            "agentes_chamados": ["roteador"]
        }
    
    return {
        "messages": [AIMessage(content=saida)],
        "rota": "fim",
        "agentes_chamados": ["roteador_resposta_direta"]
    }
