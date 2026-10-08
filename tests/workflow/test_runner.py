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
    enviar_mensagem_usuario = AsyncMock()
    enviar_mensagem_chatbot = AsyncMock()
    monkeypatch.setattr(runner, "enviar_mensagem_usuario", enviar_mensagem_usuario)
    monkeypatch.setattr(runner, "enviar_mensagem_chatbot", enviar_mensagem_chatbot)
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
    monkeypatch.setattr(runner, "build_tracer", Mock(return_value=None))

    asyncio.run(
        runner.execute_turn(
            "conversation-1", "texto original", workflow, user_token="token-abc"
        )
    )

    assert runner.criar_conversa_chatbot.await_args.kwargs["user_token"] == "token-abc"
    assert enviar_mensagem_usuario.await_args.args == (
        "api-conv-1",
        "texto anonimo",
        "token-abc",
    )
    config_usado = workflow.ainvoke.await_args.kwargs["config"]
    assert config_usado["configurable"] == {"thread_id": "conversation-1"}
    assert len(config_usado["callbacks"]) == 1
    assert config_usado["callbacks"][0].conversation_id == "api-conv-1"
    assert config_usado["metadata"] == {
        "conversation_id": "api-conv-1",
        "environment": runner.settings.ENVIRONMENT,
        "assistant": "ai-assistant",
        "source": "chat",
    }
    assert config_usado["tags"] == [runner.settings.ENVIRONMENT.lower()]
    assert enviar_mensagem_chatbot.await_args.args[:2] == (
        "api-conv-1",
        "resposta anonima",
    )
    assert enviar_mensagem_chatbot.await_args.args[2] == {
        "turnId": "turn-123",
        "contentAnonymized": True,
        "specialistsUsed": ["faq_reader"],
        "workflowSteps": [
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
    monkeypatch.setattr(runner, "enviar_mensagem_usuario", AsyncMock())
    monkeypatch.setattr(runner, "enviar_mensagem_chatbot", AsyncMock())
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


def test_execute_turn_injeta_memoria_existente_no_estado_inicial(monkeypatch):
    workflow = Mock()
    workflow.ainvoke = AsyncMock(
        return_value={"messages": [AIMessage(content="oi", additional_kwargs={})]}
    )
    monkeypatch.setattr(runner, "enviar_mensagem_usuario", AsyncMock())
    monkeypatch.setattr(runner, "enviar_mensagem_chatbot", AsyncMock())
    monkeypatch.setattr(
        runner, "_conversations_por_thread", {"conversation-1": "api-conv-1"}
    )
    monkeypatch.setattr(runner, "criar_conversa_chatbot", AsyncMock())
    monkeypatch.setattr(
        runner, "anonymize_text", Mock(side_effect=[("a", {}), ("b", {})])
    )
    monkeypatch.setattr(runner, "decode_user_id", Mock(return_value="user-1"))
    monkeypatch.setattr(
        runner,
        "get_user_memory",
        AsyncMock(return_value=["mora em SP", "é instalador"]),
    )

    asyncio.run(
        runner.execute_turn(
            "conversation-1", "texto", workflow, user_token="token-abc"
        )
    )

    estado_inicial = workflow.ainvoke.await_args.args[0]
    assert estado_inicial["user_id"] == "user-1"
    assert estado_inicial["user_memory"] == "- mora em SP\n- é instalador"


def test_execute_turn_nao_agenda_atualizacao_de_memoria_sem_user_id(monkeypatch):
    workflow = Mock()
    workflow.ainvoke = AsyncMock(
        return_value={"messages": [AIMessage(content="oi", additional_kwargs={})]}
    )
    monkeypatch.setattr(runner, "enviar_mensagem_usuario", AsyncMock())
    monkeypatch.setattr(runner, "enviar_mensagem_chatbot", AsyncMock())
    monkeypatch.setattr(
        runner, "_conversations_por_thread", {"conversation-1": "api-conv-1"}
    )
    monkeypatch.setattr(runner, "criar_conversa_chatbot", AsyncMock())
    monkeypatch.setattr(
        runner, "anonymize_text", Mock(side_effect=[("a", {}), ("b", {})])
    )
    monkeypatch.setattr(runner, "decode_user_id", Mock(return_value=None))
    get_user_memory = AsyncMock()
    monkeypatch.setattr(runner, "get_user_memory", get_user_memory)
    agendar = Mock()
    monkeypatch.setattr(runner, "_agendar_atualizacao_memoria", agendar)

    asyncio.run(
        runner.execute_turn(
            "conversation-1", "texto", workflow, user_token="token-invalido"
        )
    )

    get_user_memory.assert_not_awaited()
    agendar.assert_not_called()


def test_execute_turn_agenda_atualizacao_de_memoria_em_background(monkeypatch):
    workflow = Mock()
    workflow.ainvoke = AsyncMock(
        return_value={"messages": [AIMessage(content="resposta", additional_kwargs={})]}
    )
    monkeypatch.setattr(runner, "enviar_mensagem_usuario", AsyncMock())
    monkeypatch.setattr(runner, "enviar_mensagem_chatbot", AsyncMock())
    monkeypatch.setattr(
        runner, "_conversations_por_thread", {"conversation-1": "api-conv-1"}
    )
    monkeypatch.setattr(runner, "criar_conversa_chatbot", AsyncMock())
    monkeypatch.setattr(
        runner, "anonymize_text", Mock(side_effect=[("a", {}), ("b", {})])
    )
    monkeypatch.setattr(runner, "decode_user_id", Mock(return_value="user-1"))
    monkeypatch.setattr(runner, "get_user_memory", AsyncMock(return_value=[]))
    extrair_fatos_atualizados = AsyncMock(return_value=["novo fato"])
    upsert_user_memory = AsyncMock()
    monkeypatch.setattr(runner, "extrair_fatos_atualizados", extrair_fatos_atualizados)
    monkeypatch.setattr(runner, "upsert_user_memory", upsert_user_memory)

    async def _run():
        await runner.execute_turn(
            "conversation-1", "texto", workflow, user_token="token-abc"
        )
        await asyncio.gather(*runner._background_tasks)

    asyncio.run(_run())

    extrair_fatos_atualizados.assert_awaited_once_with(
        [], "Usuário: texto\nAssistente: resposta"
    )
    upsert_user_memory.assert_awaited_once_with("user-1", ["novo fato"])


def test_execute_turn_nao_propaga_falha_da_atualizacao_de_memoria(monkeypatch):
    workflow = Mock()
    workflow.ainvoke = AsyncMock(
        return_value={"messages": [AIMessage(content="resposta", additional_kwargs={})]}
    )
    monkeypatch.setattr(runner, "enviar_mensagem_usuario", AsyncMock())
    monkeypatch.setattr(runner, "enviar_mensagem_chatbot", AsyncMock())
    monkeypatch.setattr(
        runner, "_conversations_por_thread", {"conversation-1": "api-conv-1"}
    )
    monkeypatch.setattr(runner, "criar_conversa_chatbot", AsyncMock())
    monkeypatch.setattr(
        runner, "anonymize_text", Mock(side_effect=[("a", {}), ("b", {})])
    )
    monkeypatch.setattr(runner, "decode_user_id", Mock(return_value="user-1"))
    monkeypatch.setattr(runner, "get_user_memory", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        runner,
        "extrair_fatos_atualizados",
        AsyncMock(side_effect=RuntimeError("groq e gemini fora do ar")),
    )
    monkeypatch.setattr(runner, "upsert_user_memory", AsyncMock())

    async def _run():
        resultado = await runner.execute_turn(
            "conversation-1", "texto", workflow, user_token="token-abc"
        )
        await asyncio.gather(*runner._background_tasks)
        return resultado

    resultado = asyncio.run(_run())

    assert resultado["messages"][0].content == "resposta"


def test_execute_turn_inclui_o_tracer_do_langsmith_nos_callbacks_quando_ligado(
    monkeypatch,
):
    workflow = Mock()
    workflow.ainvoke = AsyncMock(
        return_value={"messages": [AIMessage(content="ok")], "turn_agents": []}
    )
    tracer = Mock(name="tracer")
    monkeypatch.setattr(runner, "enviar_mensagem_usuario", AsyncMock())
    monkeypatch.setattr(runner, "enviar_mensagem_chatbot", AsyncMock())
    monkeypatch.setattr(runner, "_conversations_por_thread", {})
    monkeypatch.setattr(
        runner, "criar_conversa_chatbot", AsyncMock(return_value="api-conv-1")
    )
    monkeypatch.setattr(
        runner,
        "anonymize_text",
        Mock(side_effect=[("texto anonimo", {}), ("resposta anonima", {})]),
    )
    monkeypatch.setattr(runner, "decode_user_id", Mock(return_value=None))
    monkeypatch.setattr(runner, "build_tracer", Mock(return_value=tracer))

    asyncio.run(
        runner.execute_turn("conversation-1", "oi", workflow, user_token="token-abc")
    )

    callbacks = workflow.ainvoke.await_args.kwargs["config"]["callbacks"]
    assert len(callbacks) == 2
    assert callbacks[1] is tracer
