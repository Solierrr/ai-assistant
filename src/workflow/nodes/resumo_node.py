# src/workflow/nodes/resumo_node.py
from langchain_core.messages import RemoveMessage, HumanMessage
from src.workflow.state import Estado
from src.core.llm import llm_groq  # Usando o modelo rápido para resumir

PROMPT_COMPACTAR = """
Você é um assistente encarregado de manter um resumo conciso de uma conversa em andamento.
Abaixo está o resumo atual (se houver) e as novas mensagens que precisam ser integradas a ele.
Crie um novo resumo combinando tudo de forma clara e focada nos pontos essenciais de finanças/agenda.

Resumo Atual:
{resumo_atual}

Novas Mensagens para incorporar:
{novas_mensagens}

Novo Resumo Final:
"""

def no_condensar_historico(estado: Estado) -> dict:
    historico_mensagens = estado.get("messages", [])
    resumo_atual = estado.get("resumo", "")

    # Se tiver menos de 5 mensagens, não faz nada e segue o fluxo
    if len(historico_mensagens) <= 5:
        return {}

    # Vamos deixar as 2 últimas mensagens vivas (para manter o contexto imediato do chat)
    # e resumir todas as anteriores.
    mensagens_para_resumir = historico_mensagens[:-2]
    mensagens_para_manter = historico_mensagens[-2:]

    # Formata as mensagens antigas em formato de texto para o LLM ler
    texto_mensagens = ""
    for msg in mensagens_para_resumir:
        autor = "Usuário" if msg.type == "human" else "Assistente"
        texto_mensagens += f"{autor}: {msg.content}\n"

    # Chama o LLM para gerar o novo resumo consolidado
    prompt_formatado = PROMPT_COMPACTAR.format(
        resumo_atual=resumo_atual if resumo_atual else "(Nenhum resumo ainda)",
        novas_mensagens=texto_mensagens
    )
    
    novo_resumo = llm_groq().invoke([HumanMessage(content=prompt_formatado)]).content.strip()

    # Cria uma lista de comandos de remoção para as mensagens que foram resumidas
    comandos_remocao = [RemoveMessage(id=msg.id) for msg in mensagens_para_resumir]

    # Retorna o novo resumo atualizado e a ordem de apagar as mensagens antigas
    return {
        "resumo": novo_resumo,
        "messages": comandos_remocao,
        "agentes_chamados": ["condensador_memoria"]
    }