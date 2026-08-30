from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from src.api.schemas.chat import (
    ChatAcceptedResponse,
    ChatRequest,
    ChatResultResponse,
)
from src.infra.messaging.event import CHATBOT_MESSAGE_RECEIVED, AgentEvent
from src.infra.messaging.publisher import publish_event
from src.infra.messaging.result_store import (
    delete_event_result,
    get_event_result,
    save_event_result,
)

router = APIRouter(tags=["chat"])


@router.post(
    "/chat",
    response_model=ChatAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enviar mensagem ao chatbot",
)
async def conversar(requisicao: ChatRequest) -> ChatAcceptedResponse:
    """Enfileira uma mensagem para processamento assíncrono pelo chatbot."""
    event = AgentEvent(
        event_type=CHATBOT_MESSAGE_RECEIVED,
        payload={
            "conversation_id": requisicao.conversation_id,
            "message": requisicao.message,
        },
    )

    await save_event_result(
        event.event_id,
        {
            "status": "queued",
            "conversation_id": requisicao.conversation_id,
        },
    )

    try:
        await publish_event(event)
    except Exception:
        await delete_event_result(event.event_id)
        raise

    return ChatAcceptedResponse(event_id=event.event_id)


@router.get(
    "/chat/{event_id}",
    response_model=ChatResultResponse,
    summary="Consultar processamento do chatbot",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Evento não encontrado ou resultado expirado."
        }
    },
)
async def consultar_resultado(event_id: UUID) -> ChatResultResponse:
    """Retorna o estado atual e o resultado temporário de um evento."""
    result = await get_event_result(event_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento não encontrado ou expirado.",
        )

    return ChatResultResponse.model_validate(result)
