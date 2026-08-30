import json
from datetime import timedelta
from uuid import UUID

import pytest
from pydantic import ValidationError

from src.infra.messaging.event import AgentEvent


def test_agent_event_gera_identificador_timestamp_e_valores_padrao():
    event = AgentEvent(
        event_type="chatbot.message.received",
        payload={"conversation_id": "conversation-123", "message": "Ola"},
    )

    assert isinstance(event.event_id, UUID)
    assert event.timestamp.utcoffset() == timedelta(0)
    assert event.version == 1
    assert event.metadata == {}


def test_agent_event_gera_identificadores_unicos():
    first_event = AgentEvent(event_type="chatbot.message.received", payload={})
    second_event = AgentEvent(event_type="chatbot.message.received", payload={})

    assert first_event.event_id != second_event.event_id


def test_to_stream_fields_serializa_todos_os_valores_como_texto():
    event = AgentEvent(
        event_type="chatbot.message.received",
        payload={"message": "Olá", "attempt": 1, "active": True},
        metadata={"source": "api"},
    )

    fields = event.to_stream_fields()

    assert set(fields) == {
        "event_id",
        "event_type",
        "timestamp",
        "version",
        "payload",
        "metadata",
    }
    assert all(isinstance(value, str) for value in fields.values())
    assert fields["event_type"] == "chatbot.message.received"
    assert fields["version"] == "1"
    assert json.loads(fields["payload"]) == event.payload
    assert json.loads(fields["metadata"]) == event.metadata
    assert "Olá" in fields["payload"]
    assert ": " not in fields["payload"]


def test_from_stream_fields_reconstroi_evento_original():
    original = AgentEvent(
        event_type="chatbot.message.received",
        payload={
            "conversation_id": "conversation-123",
            "message": "Preciso de ajuda",
        },
        metadata={"correlation_id": "correlation-456"},
    )

    restored = AgentEvent.from_stream_fields(original.to_stream_fields())

    assert restored == original


def test_from_stream_fields_aceita_metadata_ausente():
    original = AgentEvent(
        event_type="chatbot.message.received",
        payload={"message": "Ola"},
    )
    fields = original.to_stream_fields()
    fields.pop("metadata")

    restored = AgentEvent.from_stream_fields(fields)

    assert restored.metadata == {}


def test_agent_event_rejeita_tipo_vazio():
    with pytest.raises(ValidationError):
        AgentEvent(event_type="", payload={})


def test_agent_event_rejeita_versao_inferior_a_um():
    with pytest.raises(ValidationError):
        AgentEvent(event_type="chatbot.message.received", version=0, payload={})


def test_agent_event_exige_payload():
    with pytest.raises(ValidationError):
        AgentEvent(event_type="chatbot.message.received")


def test_from_stream_fields_rejeita_payload_com_json_invalido():
    event = AgentEvent(event_type="chatbot.message.received", payload={})
    fields = event.to_stream_fields()
    fields["payload"] = "{json-invalido"

    with pytest.raises(json.JSONDecodeError):
        AgentEvent.from_stream_fields(fields)
