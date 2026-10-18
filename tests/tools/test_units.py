import asyncio

import httpx
import pytest

from src.core.security.request_context import current_persona, current_user_token
from src.infra.api_core import client as api_core
from src.infra.api_core.client import ApiCoreUnavailable, list_my_units
from src.tools import units
from src.tools.units import listar_minhas_unidades, unit_tools


def _transport(handler, pedidos):
    def interno(request: httpx.Request) -> httpx.Response:
        pedidos.append(request)
        return handler(request)

    return httpx.MockTransport(interno)


def _handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/api/user-companies/me/all":
        return httpx.Response(200, json=[{"companyId": "c1"}])
    if request.url.path == "/api/local-units/company/c1":
        return httpx.Response(
            200,
            json=[
                {
                    "id": "u1",
                    "locationType": "ROOFTOP",
                    "address": {
                        "city": "Campinas",
                        "state": "SP",
                        "neighborhood": "Centro",
                    },
                }
            ],
        )
    return httpx.Response(404)


@pytest.fixture(autouse=True)
def _contexto(monkeypatch):
    monkeypatch.setattr(api_core.settings, "API_CORE_URL", "http://core.test/api")
    token = current_user_token.set("jwt-do-usuario")
    persona = current_persona.set("demandante")
    yield
    current_user_token.reset(token)
    current_persona.reset(persona)


def test_unidades_do_usuario_seguem_vinculos_e_empresas():
    pedidos: list[httpx.Request] = []

    resultado = asyncio.run(
        list_my_units("jwt-do-usuario", _transport(_handler, pedidos))
    )

    assert resultado == [
        {
            "unidade_id": "u1",
            "empresa_id": "c1",
            "cidade": "Campinas",
            "estado": "SP",
            "bairro": "Centro",
            "tipo": "ROOFTOP",
        }
    ]
    assert all(p.headers["Authorization"] == "Bearer jwt-do-usuario" for p in pedidos)


@pytest.mark.parametrize("status", [401, 403, 500])
def test_erro_do_api_core_vira_indisponivel(status):
    transport = _transport(lambda r: httpx.Response(status), [])

    with pytest.raises(ApiCoreUnavailable):
        asyncio.run(list_my_units("jwt", transport))


def test_api_core_fora_do_ar_vira_indisponivel():
    def falha(request):
        raise httpx.ConnectError("sem conexão")

    with pytest.raises(ApiCoreUnavailable):
        asyncio.run(list_my_units("jwt", _transport(falha, [])))


def test_ferramenta_devolve_as_unidades(monkeypatch):
    async def fake(token):
        assert token == "jwt-do-usuario"
        return [{"unidade_id": "u1"}]

    monkeypatch.setattr(units, "list_my_units", fake)

    assert asyncio.run(listar_minhas_unidades.ainvoke({})) == {
        "unidades": [{"unidade_id": "u1"}]
    }


def test_ferramenta_avisa_quando_nao_ha_unidades(monkeypatch):
    async def fake(token):
        return []

    monkeypatch.setattr(units, "list_my_units", fake)

    resultado = asyncio.run(listar_minhas_unidades.ainvoke({}))

    assert resultado["unidades"] == []
    assert "não tem unidades" in resultado["aviso"]


def test_ferramenta_sem_token_nao_consulta(monkeypatch):
    chamado = []

    async def fake(token):
        chamado.append(token)
        return []

    monkeypatch.setattr(units, "list_my_units", fake)
    current_user_token.set(None)

    resultado = asyncio.run(listar_minhas_unidades.ainvoke({}))

    assert "não autenticado" in resultado["erro"]
    assert chamado == []


def test_ferramenta_com_api_core_fora_do_ar_responde_com_erro(monkeypatch):
    async def fake(token):
        raise ApiCoreUnavailable("fora")

    monkeypatch.setattr(units, "list_my_units", fake)

    assert "Não consegui" in asyncio.run(listar_minhas_unidades.ainvoke({}))["erro"]


def test_profissional_nao_recebe_a_ferramenta_de_unidades():
    assert unit_tools() == [listar_minhas_unidades]

    current_persona.set("profissional")

    assert unit_tools() == []
