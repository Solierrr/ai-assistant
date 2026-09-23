"""Cliente HTTP reutilizável do api-messenger."""

import asyncio

import httpx

from src.core.config.settings import settings

_http_client: httpx.AsyncClient | None = None
_http_client_loop: asyncio.AbstractEventLoop | None = None


def get_api_messenger_client() -> httpx.AsyncClient:
    global _http_client, _http_client_loop

    current_loop = asyncio.get_running_loop()
    if _http_client is not None and _http_client_loop is None:
        _http_client_loop = current_loop

    if (
        _http_client is None
        or _http_client.is_closed
        or _http_client_loop is not current_loop
    ):
        _http_client = httpx.AsyncClient(
            base_url=settings.API_MESSENGER_URL.rstrip("/"),
            timeout=settings.API_MESSENGER_TIMEOUT_SECONDS,
        )
        _http_client_loop = current_loop
    return _http_client


async def close_api_messenger_client() -> None:
    global _http_client, _http_client_loop

    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None
        _http_client_loop = None


async def criar_conversa_chatbot(
    user_type: str, user_details: dict, user_token: str
) -> str:
    response = await get_api_messenger_client().post(
        "/messaging/conversations/chatbot-conversations",
        json={
            "userType": user_type,
            "userDetails": user_details,
            "environment": settings.ENVIRONMENT,
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )
    response.raise_for_status()
    return response.json()["id"]


async def enviar_mensagem_usuario(
    conversation_id: str, content: str, user_token: str
) -> None:
    response = await get_api_messenger_client().post(
        "/messaging/messages",
        json={
            "conversationId": conversation_id,
            "messageType": "USER_TO_CHATBOT",
            "role": "user",
            "content": content,
            "environment": settings.ENVIRONMENT,
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )
    response.raise_for_status()


async def enviar_mensagem_chatbot(
    conversation_id: str, content: str, metadata: dict | None = None
) -> None:
    response = await get_api_messenger_client().post(
        "/internal/messages",
        json={
            "conversationId": conversation_id,
            "content": content,
            "metadata": metadata,
            "environment": settings.ENVIRONMENT,
        },
    )
    response.raise_for_status()


async def enviar_observabilidade(payload: dict) -> None:
    response = await get_api_messenger_client().post(
        "/internal/observability",
        json={**payload, "environment": settings.ENVIRONMENT},
    )
    response.raise_for_status()
