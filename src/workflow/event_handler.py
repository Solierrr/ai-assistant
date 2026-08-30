from typing import Any

from src.infra.messaging.event import AgentEvent
from src.workflow.runner import execute_turn

CHATBOT_MESSAGE_RECEIVED = "chatbot.message.received"


def get_required_payload_text(event: AgentEvent, field: str) -> str:
    value = event.payload.get(field)

    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Campo obrigatório inválido no payload: {field}")
    return value


async def handle_chat_event(
    event: AgentEvent,
    workflow: Any | None = None,
) -> dict[str, Any]:
    if event.event_type != CHATBOT_MESSAGE_RECEIVED:
        raise ValueError(f"Tipo do evento não suportado: {event.event_type}")

    conversation_id = get_required_payload_text(event, "conversation_id")
    message = get_required_payload_text(event, "message")

    if workflow is None:
        from src.workflow.graph.graph import compiled_app

        workflow = compiled_app

    final_state = await execute_turn(
        conversation_id,
        message,
        workflow,
        event_id=str(event.event_id),
    )

    final_message = final_state["messages"][-1]
    metadata = final_message.additional_kwargs

    return {
        "status": "completed",
        "conversation_id": conversation_id,
        "response": final_message.content,
        "specialists_used": metadata.get("specialists_used", []),
        "workflow_steps": metadata.get(
            "workflow_steps",
            final_state.get("turn_agents", []),
        ),
    }
