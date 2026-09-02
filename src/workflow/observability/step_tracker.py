import time
from datetime import datetime, timezone

from langchain_core.callbacks import AsyncCallbackHandler

from src.infra.api_messenger.client import enviar_observabilidade


class StepTracker(AsyncCallbackHandler):
    def __init__(self, conversation_id: str, environment: str):
        self.conversation_id = conversation_id
        self.environment = environment
        self.step_order = 0
        self._starts = {}
        self._node_by_run = {}
        self._tool_name_by_run = {}

    def _next_order(self) -> int:
        self.step_order += 1
        return self.step_order

    async def _salvar(self, node: str, doc: dict) -> None:
        doc = {
            "conversationId": self.conversation_id,
            "node": node,
            "stepOrder": self._next_order(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **doc,
        }
        try:
            await enviar_observabilidade(doc)
        except Exception:
            pass  # observabilidade nunca pode derrubar o fluxo principal

    async def on_llm_start(self, serialized, prompts, *, run_id, metadata=None, **kwargs):
        self._starts[run_id] = time.perf_counter()
        self._node_by_run[run_id] = (metadata or {}).get("langgraph_node", "desconhecido")

    async def on_llm_end(self, response, *, run_id, **kwargs):
        latency_ms = (time.perf_counter() - self._starts.pop(run_id, time.perf_counter())) * 1000
        node = self._node_by_run.pop(run_id, "desconhecido")
        generation = response.generations[0][0]
        message = getattr(generation, "message", None)
        usage = getattr(message, "usage_metadata", None) if message else None
        resp_metadata = getattr(message, "response_metadata", {}) if message else {}

        await self._salvar(node, {
            "stepType": "llm_call",
            "model": resp_metadata.get("model_name") or resp_metadata.get("model"),
            "tokensIn": usage.get("input_tokens") if usage else None,
            "tokensOut": usage.get("output_tokens") if usage else None,
            "latencyMs": round(latency_ms, 1),
            "status": "ok",
        })

    async def on_llm_error(self, error, *, run_id, **kwargs):
        node = self._node_by_run.pop(run_id, "desconhecido")
        await self._salvar(node, {"stepType": "llm_call", "status": "error", "error": str(error)})

    async def on_tool_start(self, serialized, input_str, *, run_id, metadata=None, **kwargs):
        self._starts[run_id] = time.perf_counter()
        self._node_by_run[run_id] = (metadata or {}).get("langgraph_node", "desconhecido")
        self._tool_name_by_run[run_id] = serialized.get("name", "tool_desconhecida")

    async def on_tool_end(self, output, *, run_id, **kwargs):
        latency_ms = (time.perf_counter() - self._starts.pop(run_id, time.perf_counter())) * 1000
        node = self._node_by_run.pop(run_id, "desconhecido")
        tool_name = self._tool_name_by_run.pop(run_id, "tool_desconhecida")
        await self._salvar(node, {
            "stepType": "tool_call",
            "toolName": tool_name,
            "latencyMs": round(latency_ms, 1),
            "status": "ok",
        })
