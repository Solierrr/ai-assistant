from pydantic import BaseModel, Field

from src.api.outcome import TurnOutcome


class ChatRequest(BaseModel):
    """O que o cliente envia no POST /chat."""

    conversation_id: str = Field(..., examples=["b2b-empresa-42"])
    message: str = Field(..., min_length=1, examples=["Preciso de um instalador em SP"])


class ChatResponse(BaseModel):
    """O que a API devolve no POST /chat."""

    response: str
    outcome: TurnOutcome = Field(
        ...,
        description=(
            "Resultado do turno: ANSWERED (respondeu), REFUSED (guardrail recusou), "
            "DEGRADED (houve fallback) ou TOOL_FAILED (uma ferramenta falhou e a "
            "resposta saiu sem ela)."
        ),
    )
    reason: str | None = Field(
        default=None,
        description="Código do catálogo de erros; presente quando outcome não é ANSWERED.",
        examples=["OUT_OF_SCOPE"],
    )
    specialists_used: list[str] = Field(default_factory=list)
    workflow_steps: list[str] = Field(default_factory=list)
    messenger_conversation_id: str | None = Field(
        default=None,
        description="Id da conversa no api-messenger; é o conversationId do POST /messaging/nps.",
    )
