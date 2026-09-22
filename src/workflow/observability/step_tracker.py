import asyncio
import logging
import time
from datetime import datetime, timezone

from langchain_core.callbacks import AsyncCallbackHandler

from src.infra.api_messenger.client import enviar_observabilidade

logger = logging.getLogger(__name__)


class StepTracker(AsyncCallbackHandler):
    def __init__(self, conversation_id: str, environment: str):
        self.conversation_id = conversation_id
        self.environment = environment
        self.step_order = 0
        self._starts = {}
        self._node_by_run = {}
        self._tool_name_by_run = {}
        self._model_by_run = {}
        self._pending_tasks: set[asyncio.Task] = set()

    def _next_order(self) -> int:
        self.step_order += 1
        return self.step_order

    async def _salvar(self, node: str, doc: dict) -> None:
        try:
            await enviar_observabilidade(doc)
        except Exception as erro:  # noqa: BLE001
            logger.warning("Falha ao enviar observabilidade (node=%s): %s", node, erro)

    def _agendar(self, node: str, doc: dict) -> None:
        doc = {
            "conversationId": self.conversation_id,
            "node": node,
            "stepOrder": self._next_order(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **doc,
        }
        task = asyncio.create_task(self._salvar(node, doc))
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)

    async def flush(self, timeout_seconds: float = 0.25) -> None:
        pending = tuple(self._pending_tasks)
        if not pending:
            return

        _, unfinished = await asyncio.wait(pending, timeout=timeout_seconds)
        for task in unfinished:
            task.cancel()
        if unfinished:
            await asyncio.gather(*unfinished, return_exceptions=True)

    async def on_llm_start(
        self, serialized, prompts, *, run_id, metadata=None, **kwargs
    ):
        self._starts[run_id] = time.perf_counter()
        self._node_by_run[run_id] = (metadata or {}).get(
            "langgraph_node", "desconhecido"
        )
        serialized = serialized or {}
        serialized_id = serialized.get("id") or []
        self._model_by_run[run_id] = (
            serialized.get("name")
            or (serialized_id[-1] if serialized_id else None)
            or "desconhecido"
        )

    async def on_llm_end(self, response, *, run_id, **kwargs):
        latency_ms = (
            time.perf_counter() - self._starts.pop(run_id, time.perf_counter())
        ) * 1000
        node = self._node_by_run.pop(run_id, "desconhecido")
        generation = response.generations[0][0]
        message = getattr(generation, "message", None)
        usage = getattr(message, "usage_metadata", None) if message else None
        resp_metadata = getattr(message, "response_metadata", {}) if message else {}
        started_model = self._model_by_run.pop(run_id, "desconhecido")
        tokens_in = int((usage or {}).get("input_tokens") or 0)
        tokens_out = int((usage or {}).get("output_tokens") or 0)
        model = (
            resp_metadata.get("model_name")
            or resp_metadata.get("model")
            or started_model
        )

        self._agendar(
            node,
            {
                "stepType": "LLM_CALL",
                "model": model,
                "tokensIn": tokens_in,
                "tokensOut": tokens_out,
                "tokensTotal": tokens_in + tokens_out,
                "latencyMs": round(latency_ms, 1),
                "status": True,
            },
        )

    async def on_llm_error(self, error, *, run_id, **kwargs):
        node = self._node_by_run.pop(run_id, "desconhecido")
        latency_ms = (
            time.perf_counter() - self._starts.pop(run_id, time.perf_counter())
        ) * 1000
        self._agendar(
            node,
            {
                "stepType": "LLM_CALL",
                "model": self._model_by_run.pop(run_id, "desconhecido"),
                "tokensIn": 0,
                "tokensOut": 0,
                "tokensTotal": 0,
                "latencyMs": round(latency_ms, 1),
                "status": False,
                "error": str(error),
            },
        )

    async def on_tool_start(
        self, serialized, input_str, *, run_id, metadata=None, **kwargs
    ):
        self._starts[run_id] = time.perf_counter()
        self._node_by_run[run_id] = (metadata or {}).get(
            "langgraph_node", "desconhecido"
        )
        self._tool_name_by_run[run_id] = serialized.get("name", "tool_desconhecida")

    async def on_tool_end(self, output, *, run_id, **kwargs):
        latency_ms = (
            time.perf_counter() - self._starts.pop(run_id, time.perf_counter())
        ) * 1000
        node = self._node_by_run.pop(run_id, "desconhecido")
        tool_name = self._tool_name_by_run.pop(run_id, "tool_desconhecida")
        self._agendar(
            node,
            {
                "stepType": "TOOL_CALL",
                "toolName": tool_name,
                "model": "not_applicable",
                "tokensIn": 0,
                "tokensOut": 0,
                "tokensTotal": 0,
                "latencyMs": round(latency_ms, 1),
                "status": True,
            },
        )

    async def on_tool_error(self, error, *, run_id, **kwargs):
        latency_ms = (
            time.perf_counter() - self._starts.pop(run_id, time.perf_counter())
        ) * 1000
        node = self._node_by_run.pop(run_id, "desconhecido")
        tool_name = self._tool_name_by_run.pop(run_id, "tool_desconhecida")
        self._agendar(
            node,
            {
                "stepType": "TOOL_CALL",
                "toolName": tool_name,
                "model": "not_applicable",
                "tokensIn": 0,
                "tokensOut": 0,
                "tokensTotal": 0,
                "latencyMs": round(latency_ms, 1),
                "status": False,
                "error": str(error),
            },
        )
