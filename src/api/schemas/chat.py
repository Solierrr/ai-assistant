from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    """O que o cliente envia no POST /chat."""

    conversation_id: str = Field(
        ...,
        min_length=1,
        examples=["b2b-empresa-42"],
    )
    message: str = Field(..., min_length=1, examples=["Preciso de um instalador em SP"])

    @field_validator("conversation_id", "message")
    @classmethod
    def validate_non_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("O campo não pode conter apenas espaços.")
        return value


class ChatResponse(BaseModel):
    """Contrato legado mantido temporariamente para compatibilidade de imports."""

    response: str
    specialists_used: list[str] = Field(default_factory=list)
    workflow_steps: list[str] = Field(default_factory=list)


class ChatAcceptedResponse(BaseModel):
    """Confirma que a mensagem foi adicionada à fila."""

    event_id: UUID
    status: Literal["queued"] = "queued"


class ChatResultResponse(BaseModel):
    """Representa o estado e o resultado temporário do processamento."""

    event_id: UUID
    status: Literal["queued", "processing", "retrying", "completed", "failed"]
    conversation_id: str | None = None
    response: str | None = None
    error: str | None = None
    attempts: int | None = Field(default=None, ge=1)
    max_attempts: int | None = Field(default=None, ge=1)
    specialists_used: list[str] = Field(default_factory=list)
    workflow_steps: list[str] = Field(default_factory=list)
