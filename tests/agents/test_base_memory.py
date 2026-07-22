import asyncio
from unittest.mock import AsyncMock, Mock

from src.agents.base import base_memory


def test_get_recent_history_limita_mensagens():
    resultado = base_memory.get_recent_history({"messages": [1, 2, 3]}, limit=2)

    assert resultado == [2, 3]


def test_get_user_context_data_retorna_dados_da_conversa(monkeypatch):
    repo = Mock()
    repo.find_by_id = AsyncMock(
        return_value={
            "user_type": "fornecedor",
            "user_details": {"empresa": "Solaria"},
        }
    )
    monkeypatch.setattr(base_memory, "ConversationRepository", Mock(return_value=repo))

    resultado = asyncio.run(base_memory.get_user_context_data("conv-1"))

    assert resultado == ("fornecedor", {})
    repo.find_by_id.assert_awaited_once_with("conv-1")


def test_get_user_context_data_retorna_vazio_quando_nao_ha_conversa(monkeypatch):
    repo = Mock()
    repo.find_by_id = AsyncMock(return_value=None)
    monkeypatch.setattr(base_memory, "ConversationRepository", Mock(return_value=repo))

    resultado = asyncio.run(base_memory.get_user_context_data("conv-1"))

    assert resultado == (None, {})


def test_log_interaction_persiste_schema_serializado(monkeypatch):
    repo = Mock()
    repo.save_message = AsyncMock()
    schema = Mock()
    schema.model_dump.return_value = {"conversation_id": "conv-1", "content": "ola"}
    schema_factory = Mock(return_value=schema)
    monkeypatch.setattr(base_memory, "MessageRepository", Mock(return_value=repo))
    monkeypatch.setattr(base_memory, "MessageSchema", schema_factory)

    asyncio.run(base_memory.log_interaction("conv-1", "user", "ola", agent="roteador"))

    assert schema_factory.call_args.kwargs["conversation_id"] == "conv-1"
    assert schema_factory.call_args.kwargs["agent"] == "roteador"
    repo.save_message.assert_awaited_once_with(schema.model_dump.return_value)


def test_set_active_agent_atualiza_repositorio(monkeypatch):
    repo = Mock()
    repo.update_active_agent = AsyncMock()
    monkeypatch.setattr(base_memory, "ConversationRepository", Mock(return_value=repo))

    asyncio.run(base_memory.set_active_agent("conv-1", "faq_reader"))

    repo.update_active_agent.assert_awaited_once_with("conv-1", "faq_reader")
