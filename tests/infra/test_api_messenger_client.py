import respx
from httpx import Response

from src.infra.api_messenger import client


@respx.mock
async def test_criar_conversa_usa_token_do_usuario_sem_autenticar_servico(monkeypatch):
    monkeypatch.setattr(client.settings, "API_MESSENGER_URL", "http://api-messenger")
    monkeypatch.setattr(client.settings, "API_MESSENGER_CLIENT_SECRET", "segredo")
    monkeypatch.setattr(client.settings, "ENVIRONMENT", "LOCAL")

    auth_route = respx.post("http://api-messenger/internal/service-tokens").mock(
        return_value=Response(
            200, json={"accessToken": "token-servico", "refreshToken": "refresh-1"}
        )
    )
    criar_route = respx.post(
        "http://api-messenger/messaging/conversations/chatbot-conversations"
    ).mock(return_value=Response(200, json={"id": "conv-1"}))

    conversation_id = await client.criar_conversa_chatbot(
        "lead", {"empresa": "Solaria"}, user_token="token-do-usuario"
    )

    assert conversation_id == "conv-1"
    assert not auth_route.called
    assert (
        criar_route.calls.last.request.headers["Authorization"]
        == "Bearer token-do-usuario"
    )


@respx.mock
async def test_criar_conversa_manda_environment_no_corpo(monkeypatch):
    monkeypatch.setattr(client.settings, "API_MESSENGER_URL", "http://api-messenger")
    monkeypatch.setattr(client.settings, "ENVIRONMENT", "QA")

    criar_route = respx.post(
        "http://api-messenger/messaging/conversations/chatbot-conversations"
    ).mock(return_value=Response(200, json={"id": "conv-1"}))

    await client.criar_conversa_chatbot("lead", {}, user_token="token-do-usuario")

    import json

    corpo = json.loads(criar_route.calls.last.request.content)
    assert corpo["environment"] == "QA"


@respx.mock
async def test_reaproveita_token_depois(monkeypatch):
    monkeypatch.setattr(client, "_access_token", "token-existente")
    monkeypatch.setattr(client, "_refresh_token", "refresh-existente")
    monkeypatch.setattr(client.settings, "API_MESSENGER_URL", "http://api-messenger")
    monkeypatch.setattr(client.settings, "API_MESSENGER_CLIENT_SECRET", "segredo")
    monkeypatch.setattr(client.settings, "ENVIRONMENT", "LOCAL")

    auth_route = respx.post("http://api-messenger/internal/service-tokens").mock(
        return_value=Response(
            200, json={"accessToken": "token-novo", "refreshToken": "refresh-novo"}
        )
    )
    mensagem_route = respx.post("http://api-messenger/internal/messages").mock(
        return_value=Response(200, json={})
    )

    await client.enviar_mensagem_chatbot("conv-1", "ola", {"turn_id": "t-1"})
    await client.enviar_mensagem_chatbot("conv-1", "de novo", {"turn_id": "t-2"})

    assert not auth_route.called
    assert mensagem_route.call_count == 2
    assert (
        mensagem_route.calls.last.request.headers["Authorization"]
        == "Bearer token-existente"
    )


@respx.mock
async def test_enviar_mensagem_manda_environment_no_corpo(monkeypatch):
    monkeypatch.setattr(client, "_access_token", "token-existente")
    monkeypatch.setattr(client, "_refresh_token", "refresh-existente")
    monkeypatch.setattr(client.settings, "API_MESSENGER_URL", "http://api-messenger")
    monkeypatch.setattr(client.settings, "ENVIRONMENT", "PROD")

    mensagem_route = respx.post("http://api-messenger/internal/messages").mock(
        return_value=Response(200, json={})
    )

    await client.enviar_mensagem_chatbot("conv-1", "ola", {"turn_id": "t-1"})

    import json

    corpo = json.loads(mensagem_route.calls.last.request.content)
    assert corpo["environment"] == "PROD"
