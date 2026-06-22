from src.workflow.state import Estado
from langchain_core.messages import RemoveMessage, SystemMessage, HumanMessage, AIMessage
from src.core.llm.llm_groq import llm_groq
from src.core.guardrails.anonymize import anonimizar_texto
from src.prompts.system_prompts import PROMPT_GUARDRAIL_ENTRADA

def no_guardrail_entrada(estado: Estado) -> dict:
    ultima_msg = estado["messages"][-1].content
    
    texto_anonimo, mapa_pii = anonimizar_texto(ultima_msg)
    
    prompt_formatado = PROMPT_GUARDRAIL_ENTRADA.format(mensagem=texto_anonimo)
    resposta = llm_groq().invoke([HumanMessage(content=prompt_formatado)]).content
    
    if "BLOQUEADO" in resposta.upper():
        return {
            "messages": [RemoveMessage(id=estado["messages"][-1].id), 
                        AIMessage(content="Desculpe, não posso processar essa solicitação por políticas de segurança.")],
            "rota": "fim",
            "pii_map": mapa_pii,
            "agentes_chamados": ["guardrail_entrada_bloqueado"]
        }
        
    return {
        "messages": [RemoveMessage(id=estado["messages"][-1].id),
                    HumanMessage(content=texto_anonimo)],
        "rota": "proseguir",
        "pii_map": mapa_pii,
        "agentes_chamados": ["guardrail_entrada_aprovado"]
    }