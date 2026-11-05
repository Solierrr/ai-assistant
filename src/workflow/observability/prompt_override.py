from typing import Any

from langchain_core.callbacks import AsyncCallbackHandler

from src.workflow.observability.llm_dedupe import DuplicateRuns


class PromptOverride(AsyncCallbackHandler):
    run_inline = True

    def __init__(self, node: str, overrides: dict[int, dict[int, str]]) -> None:
        self.node = node
        self.overrides = overrides
        self.calls = 0
        self.applied = 0
        self._dedupe = DuplicateRuns()

    async def on_llm_end(self, response, *, run_id, **kwargs: Any):
        self._dedupe.finish(run_id)

    async def on_llm_error(self, error, *, run_id, **kwargs: Any):
        self._dedupe.finish(run_id)

    async def on_chat_model_start(
        self, serialized, messages, *, run_id, metadata=None, **kwargs: Any
    ):
        if (metadata or {}).get("langgraph_node") != self.node:
            return
        if self._dedupe.start(run_id, self.node, messages):
            return
        call, self.calls = self.calls, self.calls + 1
        wanted = self.overrides.get(call)
        if not wanted:
            return
        for group in messages:
            for position, new_text in wanted.items():
                if position >= len(group) or not editable_message(group[position]):
                    continue
                if group[position].content != new_text:
                    group[position].content = new_text
                    self.applied += 1


def editable_message(message) -> bool:
    """Qualquer mensagem do prompt (system, human, ai) pode ser editada.

    Ficam de fora as que carregam decisão de tool: o resultado de uma tool e a
    mensagem do modelo que pediu uma tool.
    """
    if message.type == "tool":
        return False
    return not getattr(message, "tool_calls", None)
