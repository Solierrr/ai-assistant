from fastapi import APIRouter

from src.api.schemas.chat import ChatRequest, ChatResponse
from src.workflow.runner import execute_turn

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def conversar(requisicao: ChatRequest) -> ChatResponse:
    """Recebe uma mensagem do usuário e devolve a resposta do assistente."""
    from src.workflow.graph.graph import compiled_app

    final_state = await execute_turn(
        requisicao.conversation_id,
        requisicao.message,
        compiled_app,
    )
    final_message = final_state["messages"][-1]
    metadata = final_message.additional_kwargs

    return ChatResponse(
        response=final_message.content,
        specialists_used=metadata.get("specialists_used", []),
        workflow_steps=metadata.get(
            "workflow_steps", final_state.get("turn_agents", [])
        ),
    )
