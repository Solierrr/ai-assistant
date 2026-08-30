from uuid import uuid4

from langchain_core.messages import HumanMessage

from src.agents.base.base_memory import log_interaction
from src.core.guardrails.anonymize import anonymize_text


async def execute_turn(
    conversation_id: str,
    user_input: str,
    workflow,
    event_id: str | None = None,
) -> dict:
    turn_id = str(uuid4())
    anonymized_user_input, _ = anonymize_text(user_input)

    user_metadata = {
        "turn_id": turn_id,
        "content_anonymized": True,
    }

    if event_id is not None:
        user_metadata["event_id"] = event_id

    await log_interaction(
        conversation_id,
        "user",
        anonymized_user_input,
        metadata=user_metadata,
    )

    final_state = await workflow.ainvoke(
        {
            "messages": [HumanMessage(content=user_input)],
            "route": "",
            "pii_map": {},
            "turn_agents": [],
            "judge_retries": 0,
        },
        config={"configurable": {"thread_id": conversation_id}},
    )

    final_message = final_state["messages"][-1]
    anonymized_assistant_response, _ = anonymize_text(final_message.content)
    message_metadata = final_message.additional_kwargs
    audit_metadata = {
        "turn_id": turn_id,
        "content_anonymized": True,
        "specialists_used": message_metadata.get("specialists_used", []),
        "workflow_steps": message_metadata.get(
            "workflow_steps", final_state.get("turn_agents", [])
        ),
    }

    if event_id is not None:
        audit_metadata["event_id"] = event_id

    await log_interaction(
        conversation_id,
        "assistant",
        anonymized_assistant_response,
        metadata=audit_metadata,
    )

    return final_state
