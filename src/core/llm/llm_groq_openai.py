import logging
from typing import Any

from ai_lib.llm import configured_providers
from langchain_core.callbacks import BaseCallbackHandler

from src.core.llm.keys import key_client
from src.core.llm.llm_groq import llm_groq
from src.core.llm.llm_openai import llm_openai

logger = logging.getLogger(__name__)


class _LogFalhaDoProvedor(BaseCallbackHandler):
    """Registra o erro de cada provedor.

    Quando todos falham, o LangChain relança só o erro do primeiro, e o do fallback
    some. Com isso o erro da OpenAI continua visível no log.
    """

    raise_error = False

    def __init__(self, provedor: str) -> None:
        self.provedor = provedor

    def on_llm_error(self, error: BaseException, **kwargs: Any) -> None:
        logger.warning(
            "Falha no provedor de LLM %s: %s: %s",
            self.provedor,
            type(error).__name__,
            error,
        )


def llm_groq_openai(temperature=0.7):
    """Groq como principal e OpenAI (LLM_MODEL_OPENAI, ex.: gpt-6-luna) como fallback.

    Sem chave ou sem modelo da OpenAI, devolve só o Groq e avisa no log.
    """
    key_client()
    groq = llm_groq(temperature=temperature).with_config(
        callbacks=[_LogFalhaDoProvedor("groq")]
    )
    if "openai" not in configured_providers():
        logger.warning("OpenAI sem chave utilizável: o Groq fica sem fallback.")
        return groq
    try:
        openai = llm_openai(temperature=temperature)
    except ValueError as erro:
        logger.warning(
            "OpenAI sem modelo configurado: o Groq fica sem fallback (%s).", erro
        )
        return groq
    return groq.with_fallbacks(
        [openai.with_config(callbacks=[_LogFalhaDoProvedor("openai")])]
    )
