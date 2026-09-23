from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    """Mensagem enviada ao chatbot."""

    conversation_id: str = Field(..., min_length=1, examples=["b2b-empresa-42"])
    message: str = Field(
        ..., min_length=1, max_length=8_000, examples=["Preciso de um instalador em SP"]
    )

    @field_validator("conversation_id", "message")
    @classmethod
    def validate_non_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("O campo não pode conter apenas espaços.")
        return value


class ChatAcceptedResponse(BaseModel):
    """Confirma o recebimento da mensagem pela fila."""

    event_id: UUID
    status: Literal["queued"] = "queued"


class ChatResultResponse(BaseModel):
    """Estado temporário do processamento assíncrono."""

    event_id: UUID
    status: Literal["queued", "processing", "completed", "failed"]
    conversation_id: str | None = None
    response: str | None = None
    error: str | None = None
    error_type: str | None = None
    queued_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    queue_wait_ms: int | None = Field(default=None, ge=0)
    processing_time_ms: int | None = Field(default=None, ge=0)
    total_time_ms: int | None = Field(default=None, ge=0)
    specialists_used: list[str] = Field(default_factory=list)
    workflow_steps: list[str] = Field(default_factory=list)
