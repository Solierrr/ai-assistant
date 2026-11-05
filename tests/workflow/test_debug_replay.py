import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, MessagesState, StateGraph

from src.workflow.debug_replay import ReplayError, run_single_node
from src.workflow.observability.debug_tracker import DebugTracker

THREAD = "debug:admin:conv"


class _Eco(FakeMessagesListChatModel):
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        texto = "|".join(m.content for m in messages if m.type == "system")
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=texto))]
        )


_llm = _Eco(responses=[AIMessage(content="x")])


class _Estado(MessagesState):
    route: str


def _entrada(state, config=None):
    _llm.invoke(
        [SystemMessage(content="PROMPT-ENTRADA"), *state["messages"]], config=config
    )
    return {"route": "especialista"}


def _router(state, config=None):
    _llm.invoke(
        [SystemMessage(content="PROMPT-ROUTER"), *state["messages"]], config=config
    )
    return {"route": "especialista" if len(state["messages"]) < 3 else "fim"}


def _especialista(state, config=None):
    resposta = _llm.invoke(
        [SystemMessage(content="PROMPT-ESPECIALISTA"), *state["messages"]],
        config=config,
    )
    return {"messages": [AIMessage(content=resposta.content)]}


def _app():
    graph = StateGraph(_Estado)
    graph.add_node("entrada", _entrada)
    graph.add_node("router", _router)
    graph.add_node("especialista", _especialista)
    graph.set_entry_point("entrada")
    graph.add_edge("entrada", "router")
    graph.add_conditional_edges(
        "router", lambda s: s["route"], {"especialista": "especialista", "fim": END}
    )
    graph.add_edge("especialista", "router")
    return graph.compile(checkpointer=InMemorySaver())


async def _turno(app, texto="oi"):
    await app.ainvoke(
        {"messages": [HumanMessage(content=texto)]},
        {"configurable": {"thread_id": THREAD}},
    )


async def _rodar(
    app, node, *, turn=0, occurrence=0, overrides=None, collector=None, **edits
):
    return await run_single_node(
        app,
        THREAD,
        turn=turn,
        node=node,
        occurrence=occurrence,
        overrides=overrides or {},
        callbacks=[collector or DebugTracker()],
        metadata={},
        tags=[],
        **edits,
    )


async def _historico(app):
    return [
        s async for s in app.aget_state_history({"configurable": {"thread_id": THREAD}})
    ]


async def test_roda_so_o_no_e_para_nele():
    app = _app()
    await _turno(app)
    collector = DebugTracker()

    _, proximos, aplicados, _ = await _rodar(
        app, "especialista", collector=collector
    )

    nos = collector.snapshot()["nodes"]
    assert [n["node"] for n in nos] == ["especialista"]
    assert proximos == ("router",)
    assert aplicados == 0


async def test_troca_o_prompt_system_e_o_debug_registra_o_texto_enviado():
    app = _app()
    await _turno(app)
    collector = DebugTracker()

    _, _, aplicados, _ = await _rodar(
        app, "especialista", overrides={0: {0: "PROMPT-EDITADO"}}, collector=collector
    )

    chamada = collector.snapshot()["nodes"][0]["llm_calls"][0]
    assert aplicados == 1
    assert chamada["prompt"][0] == {"type": "system", "content": "PROMPT-EDITADO"}
    assert chamada["completion"] == "PROMPT-EDITADO"
    assert chamada["prompt_complete"] is True


async def test_troca_tambem_a_mensagem_do_usuario_no_prompt():
    app = _app()
    await _turno(app)
    collector = DebugTracker()

    _, _, aplicados, _ = await _rodar(
        app, "especialista", overrides={0: {1: "texto novo"}}, collector=collector
    )

    chamada = collector.snapshot()["nodes"][0]["llm_calls"][0]
    assert aplicados == 1
    assert chamada["prompt"][1] == {"type": "human", "content": "texto novo"}


async def test_mensagem_de_tool_nao_e_editavel_no_prompt():
    from langchain_core.messages import ToolMessage

    from src.workflow.observability.prompt_override import editable_message

    assert editable_message(HumanMessage(content="a"))
    assert editable_message(SystemMessage(content="a"))
    assert editable_message(AIMessage(content="a"))
    assert not editable_message(ToolMessage(content="a", tool_call_id="1"))
    assert not editable_message(
        AIMessage(content="", tool_calls=[{"name": "t", "args": {}, "id": "1"}])
    )


async def test_edita_a_mensagem_do_usuario_na_entrada_do_no():
    app = _app()
    await _turno(app, "oi")
    collector = DebugTracker()

    _, _, _, editado = await _rodar(
        app, "especialista", user_message="outra pergunta", collector=collector
    )

    chamada = collector.snapshot()["nodes"][0]["llm_calls"][0]
    assert chamada["prompt"][1] == {"type": "human", "content": "outra pergunta"}
    assert editado == {"user_message": True, "messages": 1, "state": []}


async def test_edicao_da_entrada_nao_altera_a_conversa_original():
    app = _app()
    await _turno(app, "oi")
    antes = [s.config["configurable"]["checkpoint_id"] for s in await _historico(app)]

    await _rodar(app, "especialista", user_message="outra")

    depois = [s.config["configurable"]["checkpoint_id"] for s in await _historico(app)]
    assert depois == antes
    estado = await app.aget_state({"configurable": {"thread_id": THREAD}})
    assert estado.values["messages"][0].content == "oi"


async def test_edita_mensagem_por_indice():
    app = _app()
    await _turno(app, "oi")

    _, _, _, editado = await _rodar(
        app, "especialista", message_edits={0: "por indice"}
    )

    assert editado["messages"] == 1


async def test_indice_de_mensagem_inexistente_responde_422():
    app = _app()
    await _turno(app)

    with pytest.raises(ReplayError) as erro:
        await _rodar(app, "especialista", message_edits={9: "x"})

    assert erro.value.status == 422


async def test_route_e_turn_agents_nao_sao_editaveis():
    app = _app()
    await _turno(app)

    for campo in ("route", "turn_agents", "user_id"):
        with pytest.raises(ReplayError) as erro:
            await _rodar(app, "especialista", state_edits={campo: "x"})
        assert erro.value.status == 422


async def test_no_repetido_escolhe_a_ocorrencia():
    app = _app()
    await _turno(app)
    primeiro, segundo = DebugTracker(), DebugTracker()

    await _rodar(app, "router", occurrence=0, collector=primeiro)
    await _rodar(app, "router", occurrence=1, collector=segundo)

    entrada_1 = primeiro.snapshot()["nodes"][0]["input"]
    entrada_2 = segundo.snapshot()["nodes"][0]["input"]
    assert entrada_1["message_count"] < entrada_2["message_count"]


async def test_primeiro_no_do_turno_tambem_funciona():
    app = _app()
    await _turno(app)
    collector = DebugTracker()

    _, proximos, _, _ = await _rodar(app, "entrada", collector=collector)

    assert [n["node"] for n in collector.snapshot()["nodes"]] == ["entrada"]
    assert proximos == ("router",)


async def test_conversa_original_e_copia_ficam_intactas():
    app = _app()
    await _turno(app)
    antes = [s.config["configurable"]["checkpoint_id"] for s in await _historico(app)]

    await _rodar(app, "especialista", overrides={0: {0: "X"}})

    depois = [s.config["configurable"]["checkpoint_id"] for s in await _historico(app)]
    assert depois == antes
    threads = {
        c.config["configurable"]["thread_id"] for c in app.checkpointer.list(None)
    }
    assert threads == {THREAD}


async def test_segundo_turno_usa_o_indice_do_turno():
    app = _app()
    await _turno(app, "primeira")
    await _turno(app, "segunda")
    primeiro, segundo = DebugTracker(), DebugTracker()

    await _rodar(app, "entrada", turn=0, collector=primeiro)
    await _rodar(app, "entrada", turn=1, collector=segundo)

    assert (
        primeiro.snapshot()["nodes"][0]["input"]["last_message"]["content"]
        == "primeira"
    )
    assert (
        segundo.snapshot()["nodes"][0]["input"]["last_message"]["content"] == "segunda"
    )


@pytest.mark.parametrize(
    ("kwargs", "status"),
    [
        ({"node": "especialista", "turn": 5}, 404),
        ({"node": "nao_existe"}, 404),
        ({"node": "especialista", "occurrence": 9}, 404),
    ],
)
async def test_pedidos_invalidos_viram_erro_claro(kwargs, status):
    app = _app()
    await _turno(app)

    with pytest.raises(ReplayError) as erro:
        await _rodar(app, **kwargs)

    assert erro.value.status == status


async def test_no_bloqueado_responde_422_com_o_motivo(monkeypatch):
    from src.workflow import debug_replay

    monkeypatch.setitem(debug_replay.REPLAY_BLOCKED_NODES, "especialista", "sem prompt")
    app = _app()
    await _turno(app)

    with pytest.raises(ReplayError) as erro:
        await _rodar(app, "especialista")

    assert erro.value.status == 422
    assert erro.value.detail == "sem prompt"


async def test_count_turns_conta_um_por_mensagem_do_usuario():
    from src.workflow.debug_replay import count_turns

    app = _app()
    assert await count_turns(app, THREAD) == 0
    await _turno(app, "um")
    await _turno(app, "dois")

    assert await count_turns(app, THREAD) == 2


async def test_turno_inexistente_menciona_a_expiracao_dos_checkpoints():
    app = _app()
    await _turno(app)

    with pytest.raises(ReplayError) as erro:
        await _rodar(app, "especialista", turn=3)

    assert erro.value.status == 404
    assert "expiram" in erro.value.detail
