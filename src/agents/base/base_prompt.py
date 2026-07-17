from src.agents.base.system_prompt import (
    SYSTEM_CORE,
    obter_contexto_temporal,
    obter_contexto_usuario,
)


def build_system_prompt(
    specific_prompt: str,
    user_type: str | None = None,
    user_details: dict | None = None,
    include_date: bool = True,
) -> str:
    """Monta o system prompt final combinando SYSTEM_CORE, o prompt
    específico do agente e o contexto temporal/de usuário quando aplicável.
    Único lugar do projeto que deve concatenar esses blocos."""
    parts = [SYSTEM_CORE.strip(), specific_prompt.strip()]

    if include_date:
        parts.append(obter_contexto_temporal().strip())

    if user_type:
        parts.append(obter_contexto_usuario(user_type, user_details or {}).strip())

    return "\n\n".join(parts)
