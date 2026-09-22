import asyncio
from dataclasses import dataclass
from uuid import uuid4

from langchain_core.messages import HumanMessage

from src.core.config.settings import settings
from src.core.guardrails.anonymize import anonymize_text
from src.infra.api_messenger.client import (
    criar_conversa_chatbot,
    enviar_mensagem_chatbot,
    enviar_mensagem_usuario,
)
from src.workflow.observability.step_tracker import StepTracker


@dataclass(frozen=True)
class PreparedTurn:
    thread_id: str
    messenger_conversation_id: str
    user_input: str


_conversations_por_thread: dict[str, str] = {}
_conversation_locks: dict[str, asyncio.Lock] = {}


async def _get_or_create_conversation_id(thread_id: str, user_token: str) -> str:
    conversation_id = _conversations_por_thread.get(thread_id)
    if conversation_id is not None:
        return conversation_id

    lock = _conversation_locks.setdefault(thread_id, asyncio.Lock())
    async with lock:
        conversation_id = _conversations_por_thread.get(thread_id)
        if conversation_id is None:
            conversation_id = await criar_conversa_chatbot(
                "lead", {}, user_token=user_token
            )
            _conversations_por_thread[thread_id] = conversation_id
        return conversation_id


async def prepare_turn(
    thread_id: str, user_input: str, user_token: str
) -> PreparedTurn:
    anonymized_user_input, _ = anonymize_text(user_input)
    messenger_conversation_id = await _get_or_create_conversation_id(
        thread_id, user_token
    )
    await enviar_mensagem_usuario(
        messenger_conversation_id,
        anonymized_user_input,
        user_token,
    )
    return PreparedTurn(
        thread_id=thread_id,
        messenger_conversation_id=messenger_conversation_id,
        user_input=user_input,
    )


async def execute_prepared_turn(
    prepared_turn: PreparedTurn,
    workflow,
) -> dict:
    turn_id = str(uuid4())
    tracker = StepTracker(
        conversation_id=prepared_turn.messenger_conversation_id,
        environment=settings.ENVIRONMENT,
    )
    try:
        final_state = await workflow.ainvoke(
            {
                "messages": [HumanMessage(content=prepared_turn.user_input)],
                "route": "",
                "pii_map": {},
                "turn_agents": [],
                "judge_retries": 0,
            },
            config={
                "configurable": {"thread_id": prepared_turn.thread_id},
                "callbacks": [tracker],
            },
        )
    finally:
        await tracker.flush()

    final_message = final_state["messages"][-1]
    anonymized_response, _ = anonymize_text(final_message.content)
    message_metadata = final_message.additional_kwargs
    audit_metadata = {
        "turnId": turn_id,
        "contentAnonymized": True,
        "specialistsUsed": message_metadata.get("specialists_used", []),
        "workflowSteps": message_metadata.get(
            "workflow_steps", final_state.get("turn_agents", [])
        ),
    }
    await enviar_mensagem_chatbot(
        prepared_turn.messenger_conversation_id,
        anonymized_response,
        audit_metadata,
    )
    return final_state


async def execute_turn(
    conversation_id: str, user_input: str, workflow, user_token: str
) -> dict:
    prepared_turn = await prepare_turn(conversation_id, user_input, user_token)
    return await execute_prepared_turn(prepared_turn, workflow)
