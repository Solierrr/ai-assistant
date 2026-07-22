from datetime import datetime, timezone

from src.infra.database.mongo.repositories.conversation_repository import (
    ConversationRepository,
)
from src.infra.database.mongo.repositories.message_repository import (
    MessageRepository,
)
from src.infra.database.mongo.schemas.message_schema import MessageSchema


def get_recent_history(state: dict, limit: int = 10) -> list:
    """Retorna as últimas `limit` mensagens já mantidas em memória pelo
    checkpointer do LangGraph (não consulta o banco)."""
    messages = state.get("messages", [])
    return messages[-limit:]


async def get_user_context_data(conversation_id: str) -> tuple[str | None, dict]:
    """Busca tipo de usuário e detalhes de sessão persistidos, para
    alimentar build_system_prompt. Retorna (None, {}) se ainda não existir."""
    repo = ConversationRepository()
    conversation = await repo.find_by_id(conversation_id)
    if not conversation:
        return None, {}

    user_type = conversation.get("user_type")
    details = conversation.get("user_details", {})
    return user_type, details


async def log_interaction(
    conversation_id: str,
    role: str,
    content: str,
    agent: str | None = None,
    metadata: dict | None = None,
) -> None:
    """Persiste uma mensagem na coleção de longo prazo, para auditoria e
    observabilidade, independente da memória de curto prazo do LangGraph."""
    repo = MessageRepository()
    message = MessageSchema(
        conversation_id=conversation_id,
        role=role,
        content=content,
        agent=agent,
        timestamp=datetime.now(timezone.utc),
        metadata=metadata or {},
    )
    await repo.save_message(message.model_dump())


async def set_active_agent(conversation_id: str, agent: str) -> None:
    """Atualiza qual agente está tratando a conversa no momento."""
    repo = ConversationRepository()
    await repo.update_active_agent(conversation_id, agent)
