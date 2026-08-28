"""Cliente HTTP do api-messenger."""

import httpx

from src.core.config.settings import settings

_access_token: str | None = None
_refresh_token: str | None = None


async def _autenticar() -> None:
    global _access_token, _refresh_token
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.API_MESSENGER_URL}/internal/service-tokens",
            json={"clientSecret": settings.API_MESSENGER_CLIENT_SECRET},
        )
        resp.raise_for_status()
        dados = resp.json()
        _access_token = dados["accessToken"]
        _refresh_token = dados["refreshToken"]


async def _headers() -> dict:
    if _access_token is None:
        await _autenticar()
    return {"Authorization": f"Bearer {_access_token}"}


async def criar_conversa_chatbot(user_type: str, user_details: dict, user_token: str) -> str:
    """Cria a conversa com o JWT do usuário real."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.API_MESSENGER_URL}/messaging/conversations/chatbot-conversations",
            json={
                "userType": user_type,
                "userDetails": user_details,
                "environment": settings.ENVIRONMENT,
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        resp.raise_for_status()
        return resp.json()["id"]


async def enviar_mensagem_chatbot(
    conversation_id: str, content: str, metadata: dict | None = None
) -> None:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.API_MESSENGER_URL}/internal/messages",
            json={
                "conversationId": conversation_id,
                "content": content,
                "metadata": metadata,
                "environment": settings.ENVIRONMENT,
            },
            headers=await _headers(),
        )
        resp.raise_for_status()
