from src.infra.api_messenger.client import enviar_mensagem_chatbot


def get_recent_history(state: dict, limit: int = 10) -> list:
    """Retorna as últimas `limit` mensagens já mantidas em memória pelo
    checkpointer do LangGraph (não consulta o banco)."""
    messages = state.get("messages", [])
    return messages[-limit:]


async def log_interaction(
    conversation_id: str,
    role: str,
    content: str,
    agent: str | None = None,
    metadata: dict | None = None,
) -> None:
    """Registra uma mensagem na conversa do api-messenger, para auditoria e observabilidade."""
    await enviar_mensagem_chatbot(
        conversation_id,
        content,
        {"role": role, "agent": agent, **(metadata or {})},
    )
