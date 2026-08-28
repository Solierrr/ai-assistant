import asyncio
from unittest.mock import AsyncMock, Mock

from langchain_core.messages import AIMessage

import src.workflow.runner as runner


def test_execute_turn_persists_anonymized_request_and_audited_response(monkeypatch):
    workflow = Mock()
    workflow.ainvoke = AsyncMock(
        return_value={
            "messages": [
                AIMessage(
                    content="Resposta final",
                    additional_kwargs={
                        "specialists_used": ["faq_reader"],
                        "workflow_steps": [
                            "router",
                            "faq_reader",
                            "orchestrator",
                            "output_guardrail",
                        ],
                    },
                )
            ],
            "turn_agents": ["router", "faq_reader", "orchestrator"],
        }
    )
    log_interaction = AsyncMock()
    monkeypatch.setattr(runner, "log_interaction", log_interaction)
    monkeypatch.setattr(runner, "_conversations_por_thread", {})
    monkeypatch.setattr(
        runner,
        "criar_conversa_chatbot",
        AsyncMock(return_value="api-conv-1"),
    )
    monkeypatch.setattr(
        runner,
        "anonymize_text",
        Mock(side_effect=[("texto anonimo", {}), ("resposta anonima", {})]),
    )
    monkeypatch.setattr(runner, "uuid4", Mock(return_value="turn-123"))

    asyncio.run(
        runner.execute_turn(
            "conversation-1", "texto original", workflow, user_token="token-abc"
        )
    )

    assert runner.criar_conversa_chatbot.await_args.kwargs["user_token"] == "token-abc"
    assert log_interaction.await_args_list[0].args == (
        "api-conv-1",
        "user",
        "texto anonimo",
    )
    assert log_interaction.await_args_list[0].kwargs["metadata"] == {
        "turn_id": "turn-123",
        "content_anonymized": True,
    }
    assert workflow.ainvoke.await_args.kwargs["config"] == {
        "configurable": {"thread_id": "conversation-1"}
    }
    assert log_interaction.await_args_list[1].args == (
        "api-conv-1",
        "assistant",
        "resposta anonima",
    )
    assert log_interaction.await_args_list[1].kwargs["metadata"] == {
        "turn_id": "turn-123",
        "content_anonymized": True,
        "specialists_used": ["faq_reader"],
        "workflow_steps": [
            "router",
            "faq_reader",
            "orchestrator",
            "output_guardrail",
        ],
    }


def test_execute_turn_reaproveita_conversa_ja_criada_para_a_mesma_thread(monkeypatch):
    workflow = Mock()
    workflow.ainvoke = AsyncMock(
        return_value={"messages": [AIMessage(content="oi", additional_kwargs={})]}
    )
    monkeypatch.setattr(runner, "log_interaction", AsyncMock())
    monkeypatch.setattr(
        runner, "_conversations_por_thread", {"conversation-1": "api-conv-1"}
    )
    criar_conversa_chatbot = AsyncMock()
    monkeypatch.setattr(runner, "criar_conversa_chatbot", criar_conversa_chatbot)
    monkeypatch.setattr(
        runner, "anonymize_text", Mock(side_effect=[("a", {}), ("b", {})])
    )

    asyncio.run(
        runner.execute_turn(
            "conversation-1", "texto", workflow, user_token="token-abc"
        )
    )

    criar_conversa_chatbot.assert_not_awaited()
