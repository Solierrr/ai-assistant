"""Cliente local para as tools LangChain do billscanner."""

from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def get_billscanner_tools() -> list:
    """Carrega as tools do billscanner uma vez por processo."""
    from app.langchain_tools import BILLSCANNER_TOOLS

    return list(BILLSCANNER_TOOLS)
