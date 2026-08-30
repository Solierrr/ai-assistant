import json
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

CHATBOT_MESSAGE_RECEIVED = "chatbot.message.received"


class AgentEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str = Field(min_length=1)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = Field(default=1, ge=1)
    payload: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_stream_fields(self) -> dict[str, str]:
        data = self.model_dump(mode="json")

        return {
            "event_id": data["event_id"],
            "event_type": data["event_type"],
            "timestamp": data["timestamp"],
            "version": str(data["version"]),
            "payload": json.dumps(
                data["payload"],
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            "metadata": json.dumps(
                data["metadata"],
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        }

    @classmethod
    def from_stream_fields(
        cls,
        fields: Mapping[str, str],
    ) -> "AgentEvent":
        return cls(
            event_id=fields["event_id"],
            event_type=fields["event_type"],
            timestamp=fields["timestamp"],
            version=int(fields["version"]),
            payload=json.loads(fields["payload"]),
            metadata=json.loads(fields.get("metadata", "{}")),
        )
