"""Identidade da requisição em andamento.

O JWT do usuário e a persona ficam em variáveis de contexto, e não no estado do
grafo, porque o estado é gravado no checkpointer (Mongo) e o token não pode ser
persistido."""

from contextvars import ContextVar

current_user_token: ContextVar[str | None] = ContextVar(
    "current_user_token", default=None
)
current_persona: ContextVar[str] = ContextVar("current_persona", default="demandante")
