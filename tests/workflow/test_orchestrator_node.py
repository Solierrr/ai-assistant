from types import SimpleNamespace
from unittest.mock import AsyncMock

from langchain_core.messages import HumanMessage, SystemMessage

import src.workflow.nodes.orchestrator_node as node
from src.agents.base.system_prompt import (
    SYSTEM_CORE_COMMUNICATION,
    SYSTEM_CORE_SECURITY,
)
from src.agents.specialist.orchestrator.orchestrator_prompt import ORCHESTRATOR_AGENT


async def test_orchestrator_node_uses_prompt_and_provider_fallback(monkeypatch):
    invoke = AsyncMock(return_value=SimpleNamespace(content="Resposta consolidada"))
    monkeypatch.setattr(node, "invoke_model_with_fallback", invoke)
    state = {
        "messages": [HumanMessage(content="Olá")],
        "turn_agents": ["solar_panel_specialist"],
    }

    result = await node.orchestrator_node(state)

    assert result["turn_agents"] == ["solar_panel_specialist", "orchestrator"]
    assert result["messages"][0].content == "Resposta consolidada"
    messages = invoke.await_args.args[0]
    assert isinstance(messages[0], SystemMessage)
    assert SYSTEM_CORE_SECURITY.strip() in messages[0].content
    assert SYSTEM_CORE_COMMUNICATION.strip() in messages[0].content
    assert ORCHESTRATOR_AGENT.strip() in messages[0].content


async def test_orchestrator_node_keeps_summary_in_context(monkeypatch):
    invoke = AsyncMock(return_value=SimpleNamespace(content="Resposta"))
    monkeypatch.setattr(node, "invoke_model_with_fallback", invoke)

    await node.orchestrator_node(
        {
            "messages": [HumanMessage(content="Qual a garantia?")],
            "summary": "O usuário quer informações sobre painéis.",
        }
    )

    messages = invoke.await_args.args[0]
    assert "Resumo" in messages[1].content
    assert isinstance(messages[2], HumanMessage)
