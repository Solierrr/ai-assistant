import logging
from typing import Annotated, NoReturn
from uuid import UUID

import httpx
from fastapi import APIRouter, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.api.schemas.chat import (
    ChatAcceptedResponse,
    ChatRequest,
    ChatResultResponse,
)
from src.infra.messaging.event import CHATBOT_MESSAGE_RECEIVED, AgentEvent
from src.infra.messaging.publisher import publish_event
from src.infra.messaging.result_store import get_event_result
from src.workflow.runner import prepare_turn

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])

bearer_auth = HTTPBearer(
    scheme_name="bearerAuth",
    bearerFormat="JWT",
    description="Access token JWT emitido pelo api-auth.",
    auto_error=False,
)


def _extract_user_token(
    credentials: HTTPAuthorizationCredentials | None,
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header deve ser 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_token = credentials.credentials.strip()

    if not user_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de usuário não informado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_token


def _raise_api_messenger_error(error: httpx.HTTPStatusError) -> NoReturn:
    upstream_status = error.response.status_code
    if upstream_status in {401, 403}:
        raise HTTPException(
            status_code=upstream_status,
            detail="Não foi possível autenticar o usuário no api-messenger.",
        ) from error
    if 400 <= upstream_status < 500:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O api-messenger rejeitou os dados da conversa.",
        ) from error
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="O api-messenger está indisponível.",
    ) from error


@router.post(
    "/chat",
    response_model=ChatAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enviar mensagem ao chatbot",
)
async def conversar(
    requisicao: ChatRequest,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(bearer_auth),
    ],
) -> ChatAcceptedResponse:
    """Valida e persiste a mensagem antes de enfileirar seu processamento."""
    user_token = _extract_user_token(credentials)

    try:
        prepared_turn = await prepare_turn(
            requisicao.conversation_id,
            requisicao.message,
            user_token,
        )
    except httpx.HTTPStatusError as error:
        _raise_api_messenger_error(error)
    except httpx.RequestError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="O api-messenger está indisponível.",
        ) from error

    event = AgentEvent(
        event_type=CHATBOT_MESSAGE_RECEIVED,
        payload={
            "conversation_id": prepared_turn.thread_id,
            "messenger_conversation_id": prepared_turn.messenger_conversation_id,
            "message": prepared_turn.user_input,
        },
    )
    try:
        await publish_event(
            event,
            {
                "status": "queued",
                "conversation_id": prepared_turn.thread_id,
                "queued_at": event.timestamp.isoformat(),
            },
        )
    except Exception as error:
        logger.exception("Falha ao publicar evento do chatbot")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="A fila do chatbot está indisponível.",
        ) from error

    return ChatAcceptedResponse(event_id=event.event_id)


@router.get(
    "/chat/{event_id}",
    response_model=ChatResultResponse,
    response_model_exclude_none=True,
    summary="Consultar processamento do chatbot",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Evento não encontrado ou resultado expirado."
        }
    },
)
async def consultar_resultado(event_id: UUID) -> ChatResultResponse:
    """Retorna o estado atual e as métricas temporárias de um evento."""
    result = await get_event_result(event_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento não encontrado ou expirado.",
        )
    return ChatResultResponse.model_validate(result)
