import asyncio
from unittest.mock import AsyncMock

from src.agents.base import base_memory


def test_get_recent_history_limita_mensagens():
    resultado = base_memory.get_recent_history({"messages": [1, 2, 3]}, limit=2)

    assert resultado == [2, 3]


def test_log_interaction_envia_para_api_messenger(monkeypatch):
    enviar_mensagem_chatbot = AsyncMock()
    monkeypatch.setattr(base_memory, "enviar_mensagem_chatbot", enviar_mensagem_chatbot)

    asyncio.run(
        base_memory.log_interaction(
            "conv-1",
            "user",
            "ola",
            agent="roteador",
            metadata={"turn_id": "t-1"},
        )
    )

    enviar_mensagem_chatbot.assert_awaited_once_with(
        "conv-1",
        "ola",
        {"role": "user", "agent": "roteador", "turn_id": "t-1"},
    )


def test_log_interaction_sem_metadata_extra(monkeypatch):
    enviar_mensagem_chatbot = AsyncMock()
    monkeypatch.setattr(base_memory, "enviar_mensagem_chatbot", enviar_mensagem_chatbot)

    asyncio.run(base_memory.log_interaction("conv-1", "assistant", "oi"))

    enviar_mensagem_chatbot.assert_awaited_once_with(
        "conv-1",
        "oi",
        {"role": "assistant", "agent": None},
    )
