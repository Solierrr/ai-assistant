from unittest.mock import AsyncMock, Mock

from langchain_core.messages import AIMessage

from src.workflow import runner


async def test_prepare_turn_persists_anonymized_user_message(monkeypatch):
    monkeypatch.setattr(runner, "anonymize_text", Mock(return_value=("texto anonimo", {})))
    monkeypatch.setattr(
        runner, "_get_or_create_conversation_id", AsyncMock(return_value="messenger-1")
    )
    send_user = AsyncMock()
    monkeypatch.setattr(runner, "enviar_mensagem_usuario", send_user)

    prepared = await runner.prepare_turn("thread-1", "texto original", "jwt")

    assert prepared == runner.PreparedTurn("thread-1", "messenger-1", "texto original")
    send_user.assert_awaited_once_with("messenger-1", "texto anonimo", "jwt")


async def test_execute_prepared_turn_persists_audited_response(monkeypatch):
    workflow = Mock()
    workflow.ainvoke = AsyncMock(
        return_value={
            "messages": [
                AIMessage(
                    content="Resposta final",
                    additional_kwargs={"specialists_used": ["faq_reader"]},
                )
            ],
            "turn_agents": ["router", "faq_reader"],
        }
    )
    monkeypatch.setattr(runner, "anonymize_text", Mock(return_value=("resposta anonima", {})))
    monkeypatch.setattr(runner, "uuid4", Mock(return_value="turn-123"))
    send_chatbot = AsyncMock()
    monkeypatch.setattr(runner, "enviar_mensagem_chatbot", send_chatbot)

    class Tracker:
        async def flush(self):
            pass

    monkeypatch.setattr(runner, "StepTracker", Mock(return_value=Tracker()))
    prepared = runner.PreparedTurn("thread-1", "messenger-1", "texto original")

    await runner.execute_prepared_turn(prepared, workflow)

    assert workflow.ainvoke.await_args.kwargs["config"]["configurable"] == {"thread_id": "thread-1"}
    assert send_chatbot.await_args.args[:2] == ("messenger-1", "resposta anonima")
