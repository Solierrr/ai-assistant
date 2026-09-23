import logging
from typing import Any

import httpx
from google.genai.errors import APIError
from langchain.agents import create_agent

from src.agents.base.base_prompt import build_system_prompt
from src.core.llm.llm_gemini import llm_gemini
from src.core.llm.llm_groq import llm_groq

logger = logging.getLogger(__name__)
PROVIDER_ERRORS = (APIError, httpx.HTTPError, TimeoutError, ConnectionError)


def get_default_llm():
    """Retorna o modelo principal sem retries ou fallback implícitos."""
    return llm_gemini()


def build_agent(
    specific_prompt: str,
    tools: list | None = None,
    user_type: str | None = None,
    user_details: dict | None = None,
    include_date: bool = True,
    include_communication_standards: bool = True,
    model=None,
):
    """Constrói um agente com o system prompt padronizado."""
    prompt = build_system_prompt(
        specific_prompt=specific_prompt,
        include_communication_standards=include_communication_standards,
        user_type=user_type,
        user_details=user_details,
        include_date=include_date,
    )
    return create_agent(
        model=model or get_default_llm(),
        tools=tools or [],
        system_prompt=prompt,
    )


async def invoke_agent_with_fallback(
    specific_prompt: str,
    messages: list,
    *,
    tools: list | None = None,
    config: Any | None = None,
) -> dict:
    try:
        primary_agent = build_agent(
            specific_prompt,
            tools=tools,
            model=llm_gemini(),
        )
        return await primary_agent.ainvoke({"messages": messages}, config=config)
    except PROVIDER_ERRORS as error:
        logger.warning(
            "Gemini indisponível; acionando fallback Groq: %s",
            type(error).__name__,
        )

    fallback_agent = build_agent(
        specific_prompt,
        tools=tools,
        model=llm_groq(),
    )
    return await fallback_agent.ainvoke({"messages": messages}, config=config)


async def invoke_model_with_fallback(
    messages: list,
    *,
    config: Any | None = None,
):
    try:
        return await llm_gemini().ainvoke(messages, config=config)
    except PROVIDER_ERRORS as error:
        logger.warning(
            "Gemini indisponível; acionando fallback Groq: %s",
            type(error).__name__,
        )
    return await llm_groq().ainvoke(messages, config=config)
