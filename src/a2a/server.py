"""Servidor A2A do assistente: outros agentes (como o ai-geographic) delegam aqui a
escolha de produtos, profissionais e empresas."""

from ai_lib.a2a import Skill, TurnExecutor, TurnReply, TurnRequest, build_agent_card, mount_a2a
from fastapi import FastAPI, HTTPException

from src.api.auth import require_valid_token
from src.core.config.settings import settings
from src.core.security.conversation_access import ConversationAccessDenied

_SEM_TOKEN = "É preciso estar autenticado para consultar o assistente."
_TOKEN_INVALIDO = "Sua sessão expirou ou é inválida. Entre de novo para continuar."
_OUTRO_USUARIO = "Esta conversa não pertence a você."

SKILLS = [
    Skill(
        id="recomendar-produtos",
        name="Recomendar produtos, profissionais e empresas",
        description=(
            "Encontra placas solares, profissionais e empresas adequados ao contexto "
            "do usuário, a partir do ranking da api-recommendation."
        ),
        tags=["placas", "profissionais", "empresas", "recomendação"],
        examples=["Qual placa de alta eficiência serve para um telhado pequeno?"],
    )
]


def build_card():
    return build_agent_card(
        name="Assistente Solaria",
        description="Ajuda a encontrar placas solares, produtos de infraestrutura, profissionais e empresas.",
        version="0.1.0",
        base_url=settings.A2A_PUBLIC_URL,
        skills=SKILLS,
    )


async def handle_turn(request: TurnRequest) -> TurnReply:
    if not request.token:
        return TurnReply(text=_SEM_TOKEN)
    try:
        await require_valid_token(request.token)
    except HTTPException:
        return TurnReply(text=_TOKEN_INVALIDO)

    # Importado aqui para não compilar o grafo (e abrir o Mongo) ao importar o app.
    from src.workflow.graph.graph import compiled_app
    from src.workflow.runner import execute_turn

    try:
        final_state = await execute_turn(
            request.conversation_id,
            request.text,
            compiled_app,
            user_token=request.token,
            persona=request.persona,
        )
    except ConversationAccessDenied:
        return TurnReply(text=_OUTRO_USUARIO)
    return TurnReply(text=str(final_state["messages"][-1].content))


def mount(app: FastAPI) -> None:
    mount_a2a(app, build_card(), TurnExecutor(handle_turn))
