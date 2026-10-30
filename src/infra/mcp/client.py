"""Cliente MCP: conecta no api-mcp e carrega as tools disponíveis, uma vez
só, reaproveitando depois (evita reconectar a cada chamada de agente).
"""

import logging

from langchain_mcp_adapters.client import MultiServerMCPClient

from src.core.config.settings import settings

logger = logging.getLogger(__name__)

_tools_cache: list | None = None


def _headers() -> dict[str, str]:
    """Chave de serviço do assistente; a x-api-key antiga segue junto só enquanto
    MCP_API_KEY estiver definida, até o mcp-database exigir o X-Service-Key."""
    headers = {}
    if settings.SERVICE_KEY:
        headers["X-Service-Key"] = settings.SERVICE_KEY
    if settings.MCP_API_KEY:
        headers["x-api-key"] = settings.MCP_API_KEY
    return headers


async def _carregar_tools() -> list:
    client = MultiServerMCPClient(
        {
            "solaria-negocio": {
                "url": settings.MCP_URL,
                "transport": "streamable_http",
                "headers": _headers(),
            }
        }
    )
    return await client.get_tools()


async def get_mcp_tools() -> list:
    """Carrega as tools do api-mcp na primeira chamada, reaproveita depois."""
    global _tools_cache
    if _tools_cache is None:
        _tools_cache = await _carregar_tools()
    return _tools_cache


async def get_mcp_tool(nome: str):
    """Filtra uma tool específica pelo nome — cada especialista recebe só
    a ferramenta relevante pro seu domínio, não todas de uma vez."""
    tools = await get_mcp_tools()
    return [t for t in tools if t.name == nome]


async def get_mcp_tools_by_name(*nomes: str) -> list:
    """Filtra várias tools pelo nome. Avisa no log quando alguma não existe no
    servidor: sem isso, um nome desatualizado deixaria o especialista sem
    ferramenta e sem nenhum erro."""
    tools = await get_mcp_tools()
    encontradas = [t for t in tools if t.name in nomes]
    ausentes = set(nomes) - {t.name for t in encontradas}
    if ausentes:
        logger.warning("Tools MCP ausentes no servidor: %s", sorted(ausentes))
    return encontradas
