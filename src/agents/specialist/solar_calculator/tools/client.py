"""Carregador das tools de cálculo solar, usadas localmente pelo agente
(sem transporte externo — diferente das tools MCP consumidas via
src.infra.mcp.client, que vêm do serviço api-mcp)."""

from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def get_solar_calculator_tools() -> list:
    """Carrega as tools locais uma vez por processo."""
    from .langchain_tools import SOLAR_CALCULATOR_TOOLS

    return list(SOLAR_CALCULATOR_TOOLS)
