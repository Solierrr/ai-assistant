"""Leitura das unidades do usuário no api-core, com o JWT dele (vale o RBAC do api-core)."""

import httpx

from src.core.config.settings import settings

_TIMEOUT_SEGUNDOS = 15.0


class ApiCoreUnavailable(Exception):
    """O api-core não respondeu como esperado."""


async def _get(client: httpx.AsyncClient, path: str):
    resposta = await client.get(path)
    if resposta.status_code >= 400:
        raise ApiCoreUnavailable(f"{path} respondeu {resposta.status_code}")
    return resposta.json()


async def list_my_units(
    token: str, transport: httpx.AsyncBaseTransport | None = None
) -> list[dict]:
    """Unidades (locais) das empresas às quais o usuário pertence."""
    try:
        async with httpx.AsyncClient(
            base_url=settings.API_CORE_URL.rstrip("/"),
            timeout=_TIMEOUT_SEGUNDOS,
            headers={"Authorization": f"Bearer {token}"},
            transport=transport,
        ) as client:
            unidades: list[dict] = []
            perfil = await _get(client, "/users/me")
            for vinculo in perfil.get("companyMemberships") or []:
                company_id = vinculo["companyId"]
                for unidade in await _get(client, f"/local-units/company/{company_id}"):
                    endereco = unidade.get("address") or {}
                    unidades.append(
                        {
                            "unidade_id": unidade["id"],
                            "empresa_id": company_id,
                            "cidade": endereco.get("city"),
                            "estado": endereco.get("state"),
                            "bairro": endereco.get("neighborhood"),
                            "tipo": unidade.get("locationType"),
                        }
                    )
            return unidades
    except (httpx.HTTPError, KeyError, ValueError) as erro:
        raise ApiCoreUnavailable(str(erro)) from erro
