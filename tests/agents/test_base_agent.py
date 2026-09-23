from unittest.mock import AsyncMock, Mock

from src.agents.base import base_agent


def test_get_default_llm_retorna_gemini_sem_fallback_implicito(monkeypatch):
    gemini = Mock()
    monkeypatch.setattr(base_agent, "llm_gemini", Mock(return_value=gemini))

    assert base_agent.get_default_llm() is gemini


def test_build_agent_monta_prompt_e_cria_agente(monkeypatch):
    prompt = "PROMPT FINAL"
    llm = Mock()
    agent = Mock()
    monkeypatch.setattr(base_agent, "build_system_prompt", Mock(return_value=prompt))
    monkeypatch.setattr(base_agent, "get_default_llm", Mock(return_value=llm))
    monkeypatch.setattr(base_agent, "create_agent", Mock(return_value=agent))

    result = base_agent.build_agent("PROMPT", tools=["tool"])

    assert result is agent
    base_agent.create_agent.assert_called_once_with(
        model=llm, tools=["tool"], system_prompt=prompt
    )


async def test_invoke_agent_aciona_groq_uma_vez_quando_gemini_falha(monkeypatch):
    primary = Mock(ainvoke=AsyncMock(side_effect=TimeoutError("Gemini lento")))
    fallback = Mock(ainvoke=AsyncMock(return_value={"messages": []}))
    build_agent = Mock(side_effect=[primary, fallback])
    monkeypatch.setattr(base_agent, "build_agent", build_agent)
    monkeypatch.setattr(base_agent, "llm_gemini", Mock(return_value="gemini"))
    monkeypatch.setattr(base_agent, "llm_groq", Mock(return_value="groq"))
    config = {"callbacks": []}

    result = await base_agent.invoke_agent_with_fallback(
        "PROMPT", ["mensagem"], tools=["tool"], config=config
    )

    assert result == {"messages": []}
    assert build_agent.call_count == 2
    assert build_agent.call_args_list[0].kwargs["model"] == "gemini"
    assert build_agent.call_args_list[1].kwargs["model"] == "groq"
    fallback.ainvoke.assert_awaited_once_with({"messages": ["mensagem"]}, config=config)


async def test_invoke_agent_nao_faz_fallback_para_erro_de_negocio(monkeypatch):
    primary = Mock(ainvoke=AsyncMock(side_effect=ValueError("payload inválido")))
    build_agent = Mock(return_value=primary)
    monkeypatch.setattr(base_agent, "build_agent", build_agent)
    monkeypatch.setattr(base_agent, "llm_gemini", Mock(return_value="gemini"))

    try:
        await base_agent.invoke_agent_with_fallback("PROMPT", ["mensagem"])
    except ValueError as error:
        assert str(error) == "payload inválido"
    else:
        raise AssertionError("ValueError deveria ter sido propagado")

    build_agent.assert_called_once()
