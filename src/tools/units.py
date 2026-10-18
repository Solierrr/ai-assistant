from langchain_core.tools import tool

from src.core.security.request_context import current_persona, current_user_token
from src.infra.api_core.client import ApiCoreUnavailable, list_my_units


@tool
async def listar_minhas_unidades() -> dict:
    """Unidades (locais) cadastradas pelo usuário, com o id de cada uma, a cidade e o
    estado. Use o `unidade_id` nas recomendações por proximidade (`nearest_available`,
    `nearest`). Se houver mais de uma unidade, pergunte ao usuário qual usar."""
    token = current_user_token.get()
    if not token:
        return {"erro": "Usuário não autenticado."}
    try:
        unidades = await list_my_units(token)
    except ApiCoreUnavailable:
        return {"erro": "Não consegui consultar as unidades agora."}
    if not unidades:
        return {"unidades": [], "aviso": "O usuário não tem unidades cadastradas."}
    return {"unidades": unidades}


def unit_tools() -> list:
    """A ferramenta de unidades, só para o demandante: o profissional em campo não tem
    empresa nem unidades cadastradas, e recebe recomendações só com dados públicos."""
    return [] if current_persona.get() == "profissional" else [listar_minhas_unidades]
