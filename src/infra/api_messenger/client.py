"""Cliente HTTP do api-messenger."""

import httpx

from src.core.config.settings import settings


def _service_headers() -> dict:
    return {"X-Service-Key": settings.SERVICE_KEY} if settings.SERVICE_KEY else {}


async def criar_conversa_chatbot(
    user_type: str,
    user_details: dict,
    user_token: str,
    conversation_id: str | None = None,
) -> str:
    """Cria a conversa com o JWT do usuário real.

    Com `conversation_id`, o api-messenger usa esse id na conversa (e reaproveita a
    do mesmo usuário que já exista com ele); sem, gera o id."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{settings.API_MESSENGER_URL}/messaging/conversations/chatbot-conversations",
            json={
                "userType": user_type,
                "userDetails": user_details,
                "environment": settings.ENVIRONMENT,
                **({"conversationId": conversation_id} if conversation_id else {}),
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        resp.raise_for_status()
        return resp.json()["id"]


async def enviar_mensagem_chatbot(
    conversation_id: str, content: str, metadata: dict | None = None
) -> None:
    """Registra a resposta do assistente."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{settings.API_MESSENGER_URL}/internal/messages",
            json={
                "conversationId": conversation_id,
                "content": content,
                "metadata": metadata,
                "environment": settings.ENVIRONMENT,
            },
            headers=_service_headers(),
        )
        resp.raise_for_status()


async def enviar_observabilidade(payload: dict) -> None:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{settings.API_MESSENGER_URL}/internal/observability",
            json={**payload, "environment": settings.ENVIRONMENT},
            headers=_service_headers(),
        )
        resp.raise_for_status()


async def enviar_mensagem_usuario(
    conversation_id: str, content: str, user_token: str
) -> None:
    """Registra a mensagem do usuário usando seu próprio JWT."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{settings.API_MESSENGER_URL}/messaging/messages",
            json={
                "conversationId": conversation_id,
                "messageType": "USER_TO_CHATBOT",
                "role": "user",
                "content": content,
                "environment": settings.ENVIRONMENT,
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        resp.raise_for_status()
