from functools import lru_cache

from langchain_google_genai import ChatGoogleGenerativeAI

from src.core.config.settings import settings


@lru_cache(maxsize=8)
def llm_gemini(
    model: str | None = None,
    temperature: float = 0.2,
    *,
    max_tokens: int | None = None,
):
    return ChatGoogleGenerativeAI(
        model=model or settings.GEMINI_MODEL,
        temperature=temperature,
        api_key=settings.GOOGLE_API_KEY,
        request_timeout=settings.GEMINI_TIMEOUT_SECONDS,
        retries=settings.GEMINI_MAX_RETRIES,
        max_tokens=max_tokens or settings.GEMINI_MAX_TOKENS,
        thinking_level=settings.GEMINI_THINKING_LEVEL,
    )
