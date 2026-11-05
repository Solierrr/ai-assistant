import importlib
import logging

import pytest
from ai_lib.registry import RegistryKeysUnavailable
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables.fallbacks import RunnableWithFallbacks
from pydantic import ConfigDict

# `src.core.llm.llm_groq_openai` é também o nome da função exportada no pacote;
# importlib devolve o módulo, não a função.
modulo = importlib.import_module("src.core.llm.llm_groq_openai")


class _Responde(BaseChatModel):
    texto: str

    @property
    def _llm_type(self) -> str:
        return "responde"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=self.texto))]
        )


class _Falha(BaseChatModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    erro: Exception

    @property
    def _llm_type(self) -> str:
        return "falha"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        raise self.erro


GROQ_ESGOTADO = RegistryKeysUnavailable("all groq keys are resting or invalid")
PERGUNTA = [HumanMessage(content="oi")]


@pytest.fixture(autouse=True)
def ambiente(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "chave-falsa")
    monkeypatch.setenv("OPENAI_API_KEY", "chave-falsa")
    monkeypatch.setenv("LLM_MODEL_OPENAI", "gpt-6-luna")


def _com(monkeypatch, groq, openai):
    monkeypatch.setattr(modulo, "llm_groq", lambda temperature=0.7: groq)
    monkeypatch.setattr(modulo, "llm_openai", lambda temperature=0.7: openai)


def test_groq_responde_e_a_openai_nao_e_usada(monkeypatch):
    _com(
        monkeypatch,
        _Responde(texto="groq"),
        _Falha(erro=RuntimeError("nao devia ser chamada")),
    )

    assert modulo.llm_groq_openai().invoke(PERGUNTA).content == "groq"


def test_cai_na_openai_quando_as_chaves_do_groq_esgotam(monkeypatch, caplog):
    _com(monkeypatch, _Falha(erro=GROQ_ESGOTADO), _Responde(texto="luna"))

    with caplog.at_level(logging.WARNING):
        resposta = modulo.llm_groq_openai().invoke(PERGUNTA)

    assert resposta.content == "luna"
    assert "groq" in caplog.text
    assert "RegistryKeysUnavailable" in caplog.text


def test_erro_da_openai_aparece_no_log_quando_os_dois_falham(monkeypatch, caplog):
    _com(
        monkeypatch,
        _Falha(erro=GROQ_ESGOTADO),
        _Falha(erro=RuntimeError("modelo recusado")),
    )

    with caplog.at_level(logging.WARNING), pytest.raises(RegistryKeysUnavailable):
        modulo.llm_groq_openai().invoke(PERGUNTA)

    # O LangChain relança o erro do Groq (o primeiro); o da OpenAI fica só no log.
    assert "openai" in caplog.text
    assert "modelo recusado" in caplog.text


def test_cadeia_real_e_groq_depois_openai():
    cadeia = modulo.llm_groq_openai()

    assert isinstance(cadeia, RunnableWithFallbacks)
    assert cadeia.runnable.bound.provider == "groq"
    assert [m.bound.provider for m in cadeia.fallbacks] == ["openai"]
    assert cadeia.fallbacks[0].bound.model_name == "gpt-6-luna"


def test_sem_chave_da_openai_devolve_so_o_groq(monkeypatch, caplog):
    monkeypatch.delenv("OPENAI_API_KEY")

    with caplog.at_level(logging.WARNING):
        cadeia = modulo.llm_groq_openai()

    assert not isinstance(cadeia, RunnableWithFallbacks)
    assert "OpenAI sem chave" in caplog.text


def test_chave_com_marcador_do_infisical_nao_conta_como_chave(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "__preencher__")

    assert not isinstance(modulo.llm_groq_openai(), RunnableWithFallbacks)


def test_sem_modelo_da_openai_devolve_so_o_groq(monkeypatch, caplog):
    monkeypatch.delenv("LLM_MODEL_OPENAI")

    with caplog.at_level(logging.WARNING):
        cadeia = modulo.llm_groq_openai()

    assert not isinstance(cadeia, RunnableWithFallbacks)
    assert "OpenAI sem modelo configurado" in caplog.text
