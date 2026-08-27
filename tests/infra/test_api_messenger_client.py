import respx
from httpx import Response

from src.infra.api_messenger import client


@respx.mock
async def test_autentica_na_primeira_chamada(monkeypatch):
    monkeypatch.setattr(client, "_access_token", None)
    monkeypatch.setattr(client, "_refresh_token", None)
    monkeypatch.setattr(client.settings, "API_MESSENGER_URL", "http://api-messenger")
    monkeypatch.setattr(client.settings, "API_MESSENGER_CLIENT_SECRET", "segredo")

    auth_route = respx.post("http://api-messenger/internal/service-tokens").mock(
        return_value=Response(
            200, json={"accessToken": "token-1", "refreshToken": "refresh-1"}
        )
    )
    criar_route = respx.post(
        "http://api-messenger/messaging/conversations/chatbot-conversations"
    ).mock(return_value=Response(200, json={"id": "conv-1"}))

    conversation_id = await client.criar_conversa_chatbot(
        "lead", {"empresa": "Solaria"}
    )

    assert conversation_id == "conv-1"
    assert auth_route.called
    assert criar_route.calls.last.request.headers["Authorization"] == "Bearer token-1"


@respx.mock
async def test_reaproveita_token_depois(monkeypatch):
    monkeypatch.setattr(client, "_access_token", "token-existente")
    monkeypatch.setattr(client, "_refresh_token", "refresh-existente")
    monkeypatch.setattr(client.settings, "API_MESSENGER_URL", "http://api-messenger")
    monkeypatch.setattr(client.settings, "API_MESSENGER_CLIENT_SECRET", "segredo")

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
