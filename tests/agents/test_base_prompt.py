from src.agents.base import base_prompt


def test_build_system_prompt_combina_blocos_obrigatorios(monkeypatch):
    monkeypatch.setattr(base_prompt, "SYSTEM_CORE", "  CORE  ")

    resultado = base_prompt.build_system_prompt(
        "  PROMPT ESPECIFICO  ", include_date=False
    )

    assert resultado == "CORE\n\nPROMPT ESPECIFICO"


def test_build_system_prompt_inclui_contextos_opcionais(monkeypatch):
    monkeypatch.setattr(base_prompt, "SYSTEM_CORE", "CORE")
    monkeypatch.setattr(base_prompt, "obter_contexto_temporal", lambda: "DATA")
    monkeypatch.setattr(
        base_prompt,
        "obter_contexto_usuario",
        lambda user_type, details: f"USUARIO={user_type}:{details['empresa']}",
    )

    resultado = base_prompt.build_system_prompt(
        "AGENTE",
        user_type="fornecedor",
        user_details={"empresa": "Solaria"},
    )

    assert resultado == "CORE\n\nAGENTE\n\nDATA\n\nUSUARIO=fornecedor:Solaria"
