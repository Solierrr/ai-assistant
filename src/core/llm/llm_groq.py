from functools import lru_cache

from langchain_groq import ChatGroq

from src.core.config.settings import settings


@lru_cache(maxsize=16)
def llm_groq(
    model: str | None = None,
    temperature: float = 0.2,
    *,
    max_tokens: int | None = None,
):
    return ChatGroq(
        model=model or settings.GROQ_FAST_MODEL,
        temperature=temperature,
        api_key=settings.GROQ_API_KEY,
        timeout=settings.GROQ_TIMEOUT_SECONDS,
        max_retries=settings.GROQ_MAX_RETRIES,
        max_tokens=max_tokens or settings.GROQ_MAX_TOKENS,
        reasoning_effort="low",
    )
