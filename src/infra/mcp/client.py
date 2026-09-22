"""Cliente reutilizável para as ferramentas MCP do Solaria."""

from langchain_mcp_adapters.client import MultiServerMCPClient

from src.core.config.settings import settings

_tools_cache: list | None = None


async def _load_tools() -> list:
    client = MultiServerMCPClient(
        {
            "solaria-business": {
                "url": settings.MCP_URL,
                "transport": "streamable_http",
                "headers": {"x-api-key": settings.MCP_API_KEY},
            }
        }
    )
    return await client.get_tools()


async def get_mcp_tools() -> list:
    global _tools_cache

    if _tools_cache is None:
        _tools_cache = await _load_tools()
    return _tools_cache


async def get_mcp_tool(name: str) -> list:
    return [tool for tool in await get_mcp_tools() if tool.name == name]
