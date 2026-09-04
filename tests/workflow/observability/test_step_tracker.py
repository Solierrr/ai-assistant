import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import src.workflow.observability.step_tracker as step_tracker


def _resposta_llm(model="llama-3.3", tokens_in=10, tokens_out=5):
    message = SimpleNamespace(
        usage_metadata={"input_tokens": tokens_in, "output_tokens": tokens_out},
        response_metadata={"model_name": model},
    )
    generation = SimpleNamespace(message=message)
    return SimpleNamespace(generations=[[generation]])


def test_step_tracker_registra_timeline_node_a_para_node_b(monkeypatch):
    enviar = AsyncMock()
    monkeypatch.setattr(step_tracker, "enviar_observabilidade", enviar)
    tracker = step_tracker.StepTracker(conversation_id="conv-1")

    async def cenario():
        await tracker.on_llm_start(
            {}, ["prompt"], run_id="run-a", metadata={"langgraph_node": "node_a"}
        )
        await tracker.on_llm_end(_resposta_llm(), run_id="run-a")
        await tracker.on_llm_start(
            {}, ["prompt"], run_id="run-b", metadata={"langgraph_node": "node_b"}
        )
        await tracker.on_llm_end(_resposta_llm(), run_id="run-b")

    asyncio.run(cenario())

    assert enviar.await_count == 2
    doc_a = enviar.await_args_list[0].args[0]
    doc_b = enviar.await_args_list[1].args[0]
    assert doc_a["node"] == "node_a"
    assert doc_b["node"] == "node_b"


def test_step_tracker_detecta_node_sozinho_via_metadata(monkeypatch):
    enviar = AsyncMock()
    monkeypatch.setattr(step_tracker, "enviar_observabilidade", enviar)
    tracker = step_tracker.StepTracker(conversation_id="conv-1")

    asyncio.run(
        tracker.on_llm_start(
            {}, ["prompt"], run_id="run-x", metadata={"langgraph_node": "router"}
        )
    )
    asyncio.run(tracker.on_llm_end(_resposta_llm(), run_id="run-x"))

    doc = enviar.await_args.args[0]
    assert doc["node"] == "router"


def test_step_tracker_usa_desconhecido_sem_metadata(monkeypatch):
    enviar = AsyncMock()
    monkeypatch.setattr(step_tracker, "enviar_observabilidade", enviar)
    tracker = step_tracker.StepTracker(conversation_id="conv-1")

    asyncio.run(tracker.on_llm_start({}, ["prompt"], run_id="run-y"))
    asyncio.run(tracker.on_llm_end(_resposta_llm(), run_id="run-y"))

    doc = enviar.await_args.args[0]
    assert doc["node"] == "desconhecido"


def test_step_tracker_ordem_incrementa_entre_llm_e_tool(monkeypatch):
    enviar = AsyncMock()
    monkeypatch.setattr(step_tracker, "enviar_observabilidade", enviar)
    tracker = step_tracker.StepTracker(conversation_id="conv-1")

    async def cenario():
        await tracker.on_llm_start(
            {}, ["prompt"], run_id="run-1", metadata={"langgraph_node": "solar_panel_specialist"}
        )
        await tracker.on_llm_end(_resposta_llm(), run_id="run-1")
        await tracker.on_tool_start(
            {"name": "listar_ofertas_de_placas"},
            "{}",
            run_id="run-2",
            metadata={"langgraph_node": "solar_panel_specialist"},
        )
        await tracker.on_tool_end("resultado da tool", run_id="run-2")

    asyncio.run(cenario())

    doc_llm = enviar.await_args_list[0].args[0]
    doc_tool = enviar.await_args_list[1].args[0]
    assert doc_llm["stepOrder"] == 1
    assert doc_tool["stepOrder"] == 2
    assert doc_tool["stepType"] == "tool_call"
    assert doc_tool["toolName"] == "listar_ofertas_de_placas"


def test_step_tracker_inclui_conversation_id(monkeypatch):
    # Nota: self.environment não entra no doc aqui — quem estampa
    # "environment" é enviar_observabilidade (client.py), sempre a partir
    # de settings.ENVIRONMENT, não do valor recebido pelo tracker.
    enviar = AsyncMock()
    monkeypatch.setattr(step_tracker, "enviar_observabilidade", enviar)
    tracker = step_tracker.StepTracker(conversation_id="conv-42")

    asyncio.run(
        tracker.on_llm_start(
            {}, ["prompt"], run_id="run-z", metadata={"langgraph_node": "orchestrator"}
        )
    )
    asyncio.run(tracker.on_llm_end(_resposta_llm(), run_id="run-z"))

    doc = enviar.await_args.args[0]
    assert doc["conversationId"] == "conv-42"


def test_step_tracker_registra_erro_sem_derrubar_fluxo(monkeypatch):
    enviar = AsyncMock(side_effect=Exception("api-messenger fora do ar"))
    monkeypatch.setattr(step_tracker, "enviar_observabilidade", enviar)
    tracker = step_tracker.StepTracker(conversation_id="conv-1")

    asyncio.run(
        tracker.on_llm_start(
            {}, ["prompt"], run_id="run-e", metadata={"langgraph_node": "judge"}
        )
    )
    asyncio.run(tracker.on_llm_error(RuntimeError("falha no groq"), run_id="run-e"))

    doc = enviar.await_args.args[0]
    assert doc["status"] == "error"
    assert doc["error"] == "falha no groq"


def test_step_tracker_on_llm_error_manda_todos_os_campos_obrigatorios(monkeypatch):
    enviar = AsyncMock()
    monkeypatch.setattr(step_tracker, "enviar_observabilidade", enviar)
    tracker = step_tracker.StepTracker(conversation_id="conv-1")

    asyncio.run(
        tracker.on_llm_start(
            {}, ["prompt"], run_id="run-e", metadata={"langgraph_node": "judge"}
        )
    )
    asyncio.run(tracker.on_llm_error(RuntimeError("falha no groq"), run_id="run-e"))

    doc = enviar.await_args.args[0]
    assert doc["model"] == "desconhecido"
    assert doc["tokensIn"] == 0
    assert doc["tokensOut"] == 0
    assert doc["tokensTotal"] == 0
    assert isinstance(doc["latencyMs"], float)
    assert doc["status"] == "error"
    assert doc["error"] == "falha no groq"


def test_step_tracker_on_llm_end_manda_tokens_total(monkeypatch):
    enviar = AsyncMock()
    monkeypatch.setattr(step_tracker, "enviar_observabilidade", enviar)
    tracker = step_tracker.StepTracker(conversation_id="conv-1")

    asyncio.run(
        tracker.on_llm_start(
            {}, ["prompt"], run_id="run-ok", metadata={"langgraph_node": "router"}
        )
    )
    asyncio.run(
        tracker.on_llm_end(
            _resposta_llm(model="llama-3.3", tokens_in=10, tokens_out=5),
            run_id="run-ok",
        )
    )

    doc = enviar.await_args.args[0]
    assert doc["model"] == "llama-3.3"
    assert doc["tokensIn"] == 10
    assert doc["tokensOut"] == 5
    assert doc["tokensTotal"] == 15


def test_step_tracker_on_llm_end_usa_defaults_quando_usage_ausente(monkeypatch):
    # Alguns providers não populam usage_metadata/response_metadata em
    # toda resposta. O DTO exige model/tokensIn/tokensOut/tokensTotal
    # sempre não-nulos, então precisa cair num default em vez de None.
    enviar = AsyncMock()
    monkeypatch.setattr(step_tracker, "enviar_observabilidade", enviar)
    tracker = step_tracker.StepTracker(conversation_id="conv-1")

    resposta_sem_usage = SimpleNamespace(
        generations=[[SimpleNamespace(message=SimpleNamespace(usage_metadata=None, response_metadata={}))]]
    )

    asyncio.run(
        tracker.on_llm_start(
            {}, ["prompt"], run_id="run-sem-usage", metadata={"langgraph_node": "router"}
        )
    )
    asyncio.run(tracker.on_llm_end(resposta_sem_usage, run_id="run-sem-usage"))

    doc = enviar.await_args.args[0]
    assert doc["model"] == "desconhecido"
    assert doc["tokensIn"] == 0
    assert doc["tokensOut"] == 0
    assert doc["tokensTotal"] == 0


def test_step_tracker_on_tool_end_manda_campos_obrigatorios_do_llm(monkeypatch):
    # tool_call não usa LLM, mas o DTO exige model/tokens* independente
    # do stepType.
    enviar = AsyncMock()
    monkeypatch.setattr(step_tracker, "enviar_observabilidade", enviar)
    tracker = step_tracker.StepTracker(conversation_id="conv-1")

    async def cenario():
        await tracker.on_tool_start(
            {"name": "listar_ofertas_de_placas"},
            "{}",
            run_id="run-tool-ok",
            metadata={"langgraph_node": "solar_panel_specialist"},
        )
        await tracker.on_tool_end("resultado", run_id="run-tool-ok")

    asyncio.run(cenario())

    doc = enviar.await_args.args[0]
    assert doc["model"] == "n/a"
    assert doc["tokensIn"] == 0
    assert doc["tokensOut"] == 0
    assert doc["tokensTotal"] == 0


def test_step_tracker_on_tool_error_registra_falha_de_tool(monkeypatch):
    enviar = AsyncMock()
    monkeypatch.setattr(step_tracker, "enviar_observabilidade", enviar)
    tracker = step_tracker.StepTracker(conversation_id="conv-1")

    async def cenario():
        await tracker.on_tool_start(
            {"name": "listar_ofertas_de_placas"},
            "{}",
            run_id="run-t",
            metadata={"langgraph_node": "solar_panel_specialist"},
        )
        await tracker.on_tool_error(RuntimeError("mcp indisponivel"), run_id="run-t")

    asyncio.run(cenario())

    doc = enviar.await_args.args[0]
    assert doc["stepType"] == "tool_call"
    assert doc["toolName"] == "listar_ofertas_de_placas"
    assert doc["status"] == "error"
    assert doc["error"] == "mcp indisponivel"
    assert doc["model"] == "n/a"
    assert doc["tokensIn"] == 0
    assert doc["tokensOut"] == 0
    assert doc["tokensTotal"] == 0
