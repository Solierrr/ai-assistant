import json

import httpx

from src.infra.api_messenger import client


def _mock_client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url="http://api-messenger",
        transport=httpx.MockTransport(handler),
    )


async def test_rotas_publicas_usam_jwt_do_usuario(monkeypatch):
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path.endswith("chatbot-conversations"):
            return httpx.Response(201, json={"id": "conv-1"})
        return httpx.Response(201, json={})

    http_client = _mock_client(handler)
    monkeypatch.setattr(client, "_http_client", http_client)
    monkeypatch.setattr(client, "_http_client_loop", None)
    monkeypatch.setattr(client.settings, "ENVIRONMENT", "QA")

    conversation_id = await client.criar_conversa_chatbot(
        "lead", {}, "token-do-usuario"
    )
    await client.enviar_mensagem_usuario(
        conversation_id, "mensagem", "token-do-usuario"
    )

    assert conversation_id == "conv-1"
    assert all(
        request.headers["Authorization"] == "Bearer token-do-usuario"
        for request in requests
    )
    assert json.loads(requests[1].content)["environment"] == "QA"
    await http_client.aclose()


async def test_rotas_internas_nao_usam_token_m2m(monkeypatch):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(201, json={})

    http_client = _mock_client(handler)
    monkeypatch.setattr(client, "_http_client", http_client)
    monkeypatch.setattr(client, "_http_client_loop", None)

    await client.enviar_mensagem_chatbot("conv-1", "resposta", {})
    await client.enviar_observabilidade({"node": "router"})

    assert len(requests) == 2
    assert all("Authorization" not in request.headers for request in requests)
    await http_client.aclose()


async def test_cliente_http_e_reutilizado_e_fechado(monkeypatch):
    monkeypatch.setattr(client, "_http_client", None)
    monkeypatch.setattr(client, "_http_client_loop", None)
    monkeypatch.setattr(client.settings, "API_MESSENGER_URL", "http://api-messenger")

    first = client.get_api_messenger_client()
    second = client.get_api_messenger_client()
    assert first is second

    await client.close_api_messenger_client()
    assert first.is_closed
    assert client._http_client is None
    assert client._http_client_loop is None


async def test_cliente_http_nao_e_reutilizado_entre_event_loops(monkeypatch):
    current_loop = object()
    next_loop = object()
    monkeypatch.setattr(client, "_http_client", None)
    monkeypatch.setattr(client, "_http_client_loop", None)
    monkeypatch.setattr(client.settings, "API_MESSENGER_URL", "http://api-messenger")
    monkeypatch.setattr(client.asyncio, "get_running_loop", lambda: current_loop)

    first = client.get_api_messenger_client()

    monkeypatch.setattr(client.asyncio, "get_running_loop", lambda: next_loop)
    second = client.get_api_messenger_client()

    assert second is not first
    assert client._http_client_loop is next_loop

    await first.aclose()
    await client.close_api_messenger_client()
