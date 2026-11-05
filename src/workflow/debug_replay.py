import logging
from uuid import uuid4

from src.core.config.settings import settings
from src.workflow.observability.prompt_override import PromptOverride

logger = logging.getLogger(__name__)

START = "__start__"
MAX_HISTORY = 2000

REPLAY_BLOCKED_NODES: dict[str, str] = {
    "operational_delegate": (
        "Este nó delega ao ai-operational e, no debug, a delegação é simulada: "
        "não há prompt para editar."
    ),
}


class ReplayError(Exception):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


async def _turns(workflow, thread_id: str) -> list[list]:
    config = {"configurable": {"thread_id": thread_id}}
    history = []
    async for snapshot in workflow.aget_state_history(config):
        history.append(snapshot)
        if len(history) >= MAX_HISTORY:
            break
    turns: list[list] = []
    for snapshot in reversed(history):
        if snapshot.next == (START,) or not turns:
            turns.append([])
        turns[-1].append(snapshot)
    return turns


async def count_turns(workflow, thread_id: str) -> int:
    return len(await _turns(workflow, thread_id))


def check_replayable(node: str) -> None:
    reason = REPLAY_BLOCKED_NODES.get(node)
    if reason:
        raise ReplayError(422, reason)


# Campos do estado que o usuário pode alterar na ENTRADA do nó. `route` e
# `turn_agents` ficam de fora: são decisões (de roteamento e de qual agente/tool
# roda) e continuam vindo do que o fluxo de fato produziu. `user_id` também.
EDITABLE_STATE_FIELDS = frozenset(
    {
        "summary",
        "user_memory",
        "pii_map",
        "judge_retries",
        "judge_status",
        "awaiting_decision",
    }
)


def apply_input_edits(
    values: dict,
    *,
    user_message: str | None,
    message_edits: dict[int, str],
    state_edits: dict,
) -> tuple[dict, dict]:
    """Devolve (valores editados, resumo do que foi alterado) sem tocar no original."""
    from src.workflow.observability.prompt_override import editable_message

    edited = dict(values)
    summary = {"user_message": False, "messages": 0, "state": []}

    messages = list(edited.get("messages") or [])
    changes: dict[int, str] = dict(message_edits)
    if user_message is not None:
        last_human = next(
            (
                i
                for i in range(len(messages) - 1, -1, -1)
                if messages[i].type == "human"
            ),
            None,
        )
        if last_human is None:
            raise ReplayError(422, "Não há mensagem do usuário na entrada deste nó.")
        changes[last_human] = user_message
        summary["user_message"] = True

    for index, content in changes.items():
        if index >= len(messages):
            raise ReplayError(422, f"A entrada deste nó não tem a mensagem {index}.")
        if not editable_message(messages[index]):
            raise ReplayError(
                422,
                f"A mensagem {index} carrega uma decisão de tool e não pode ser editada.",
            )
        if messages[index].content != content:
            messages[index] = messages[index].model_copy(update={"content": content})
            summary["messages"] += 1
    if changes:
        edited["messages"] = messages

    for key, value in state_edits.items():
        if key not in EDITABLE_STATE_FIELDS:
            raise ReplayError(422, f"O campo de estado '{key}' não pode ser editado.")
        if edited.get(key) != value:
            edited[key] = value
            summary["state"].append(key)
    return edited, summary


async def run_single_node(
    workflow,
    thread_id: str,
    *,
    turn: int,
    node: str,
    occurrence: int,
    overrides: dict[int, dict[int, str]],
    callbacks: list,
    metadata: dict,
    tags: list[str],
    user_message: str | None = None,
    message_edits: dict[int, str] | None = None,
    state_edits: dict | None = None,
):
    check_replayable(node)
    turns = await _turns(workflow, thread_id)
    if turn >= len(turns):
        raise ReplayError(
            404,
            "Esse turno não existe nesta conversa de debug. Os checkpoints expiram "
            f"após {settings.CHECKPOINT_TTL_DIAS} dias; rode a conversa de novo.",
        )
    snapshots = turns[turn]
    candidates = [
        index for index, snapshot in enumerate(snapshots) if snapshot.next == (node,)
    ]
    if occurrence >= len(candidates):
        raise ReplayError(404, f"O nó {node} não rodou {occurrence + 1}x neste turno.")
    index = candidates[occurrence]
    target = snapshots[index]
    previous = snapshots[index - 1] if index > 0 else None
    if previous is None or len(previous.next) != 1:
        raise ReplayError(
            409, "Não foi possível reconstruir o ponto de entrada deste nó."
        )

    copy_id = f"{thread_id}:replay:{uuid4().hex[:8]}"
    copy_config = {"configurable": {"thread_id": copy_id}}
    override = PromptOverride(node, overrides)
    values, edited_inputs = apply_input_edits(
        target.values,
        user_message=user_message,
        message_edits=message_edits or {},
        state_edits=state_edits or {},
    )
    try:
        await workflow.aupdate_state(copy_config, values, as_node=previous.next[0])
        restored = await workflow.aget_state(copy_config)
        if restored.next != (node,):
            raise ReplayError(
                409,
                "O estado reconstruído não leva a este nó; a execução foi cancelada.",
            )
        state = await workflow.ainvoke(
            None,
            {
                **copy_config,
                "callbacks": [override, *callbacks],
                "metadata": metadata,
                "tags": tags,
            },
            interrupt_after=[node],
        )
        after = await workflow.aget_state(copy_config)
        return state, tuple(after.next), override.applied, edited_inputs
    finally:
        try:
            await workflow.checkpointer.adelete_thread(copy_id)
        except Exception:
            logger.warning(
                "Falha ao apagar a thread de replay %s", copy_id, exc_info=True
            )
