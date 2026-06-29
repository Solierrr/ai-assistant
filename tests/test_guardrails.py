from src.core.guardrails.anonymize import anonimizar_texto, desanonimizar_texto


def test_anonimizar_texto_substitui_cpf_e_email():
    texto = "Meu CPF e 123.456.789-00 e meu email e ana@example.com"

    texto_anonimo, mapa_pii = anonimizar_texto(texto)

    assert "123.456.789-00" not in texto_anonimo
    assert "ana@example.com" not in texto_anonimo
    assert len(mapa_pii) == 2
    assert any(token.startswith("[PII_CPF_") for token in mapa_pii)
    assert any(token.startswith("[PII_EMAIL_") for token in mapa_pii)
    assert "123.456.789-00" in mapa_pii.values()
    assert "ana@example.com" in mapa_pii.values()


def test_anonimizar_texto_sem_pii_retorna_texto_original_e_mapa_vazio():
    texto = "Quero encontrar fornecedores de paineis solares."

    texto_anonimo, mapa_pii = anonimizar_texto(texto)

    assert texto_anonimo == texto
    assert mapa_pii == {}


def test_anonimizar_texto_substitui_multiplas_ocorrencias():
    texto = "CPFs: 12345678900 e 987.654.321-00. Emails: a@x.com e b@y.com"

    texto_anonimo, mapa_pii = anonimizar_texto(texto)

    assert "12345678900" not in texto_anonimo
    assert "987.654.321-00" not in texto_anonimo
    assert "a@x.com" not in texto_anonimo
    assert "b@y.com" not in texto_anonimo
    assert len(mapa_pii) == 4


def test_desanonimizar_texto_omite_valores_originais():
    mapa_pii = {
        "[PII_CPF_abc123]": "123.456.789-00",
        "[PII_EMAIL_def456]": "ana@example.com",
    }
    texto = "Dados: [PII_CPF_abc123] e [PII_EMAIL_def456]"

    texto_final = desanonimizar_texto(texto, mapa_pii)

    assert texto_final == "Dados: [CPF OMITIDO] e [EMAIL OMITIDO]"
    assert "123.456.789-00" not in texto_final
    assert "ana@example.com" not in texto_final
