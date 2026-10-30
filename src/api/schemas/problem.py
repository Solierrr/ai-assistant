from datetime import datetime

from pydantic import BaseModel, Field


class ProblemFieldError(BaseModel):
    """Campo inválido num erro de validação."""

    field: str = Field(..., examples=["message"])
    errorCode: str = Field(..., examples=["VALIDATION_FAILED"])
    detail: str = Field(..., examples=["String should have at least 1 character"])


class ProblemDetail(BaseModel):
    """Corpo de todo erro HTTP (application/problem+json), no contrato de erro da Solaria."""

    type: str = Field(..., examples=["about:blank"])
    title: str = Field(..., examples=["UNAUTHENTICATED"])
    status: int = Field(..., examples=[401])
    errorCode: str = Field(
        ...,
        description="Código estável do catálogo de erros.",
        examples=["UNAUTHENTICATED"],
    )
    detail: str = Field(
        ...,
        description="Explicação para quem depura; o front não exibe.",
        examples=["Authorization header deve ser 'Bearer <token>'"],
    )
    instance: str = Field(..., examples=["/chat"])
    timestamp: datetime
    traceId: str | None = None
    errors: list[ProblemFieldError] | None = Field(
        default=None, description="Presente só em erros de validação."
    )
