"""Tools LangChain da calculadora solar, executadas localmente no processo
do ai-assistant (diferente das tools MCP consumidas via src.infra.mcp.client,
que rodam no serviço externo api-mcp)."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from langchain_core.tools import tool

from .calculator import (
    calcular_sistema_solar_use_case,
    geocodificar_endereco_use_case,
)
from .config import Settings
from .contracts import GeocodingResult, SolarApiClient
from .demo.client import DemoApiClient
from .normal.google_client import GoogleApiClient
from .normal.google_registry_client import GoogleRegistrySolarClient
from .service import SolarCalculationService


class _HybridSolarApiClient:
    """Geocodifica pelo Google direto e consulta potencial solar pelo
    google-registry, mantendo o contrato único de `SolarApiClient` esperado
    por `calculator.py`.

    A geocodificação permanece direta porque o google-registry ainda não
    expõe um endpoint equivalente; apenas a consulta de potencial solar é
    delegada ao serviço centralizado.
    """

    def __init__(self, settings: Settings) -> None:
        self._geocoding_client = GoogleApiClient(settings)
        self._solar_client = GoogleRegistrySolarClient(settings)

    async def geocode_address(self, address: str) -> GeocodingResult:
        return await self._geocoding_client.geocode_address(address)

    async def fetch_building_insights(
        self, latitude: float, longitude: float
    ) -> dict:
        return await self._solar_client.fetch_building_insights(latitude, longitude)


def _build_api_client(settings: Settings) -> SolarApiClient:
    if settings.demo_mode:
        return DemoApiClient(settings)
    if settings.solar_data_source == "google_registry":
        return _HybridSolarApiClient(settings)
    return GoogleApiClient(settings)


@lru_cache(maxsize=1)
def _runtime() -> tuple[Settings, SolarApiClient, SolarCalculationService]:
    settings = Settings.from_env()
    api_client = _build_api_client(settings)
    return settings, api_client, SolarCalculationService(settings)


def _serializar_resposta(resposta: Any) -> dict[str, Any]:
    if hasattr(resposta, "model_dump"):
        return resposta.model_dump(mode="json")
    if isinstance(resposta, dict):
        return resposta
    raise TypeError("A calculadora solar retornou um tipo de resposta inesperado.")


@tool
async def geocodificar_endereco(endereco: str) -> dict[str, Any]:
    """Converte um endereço brasileiro em coordenadas geográficas."""
    settings, api_client, _ = _runtime()
    resposta = await geocodificar_endereco_use_case(
        endereco,
        settings=settings,
        api_client=api_client,
    )
    return _serializar_resposta(resposta)


@tool
async def calcular_sistema_solar(
    latitude: float | None = None,
    longitude: float | None = None,
    consumo_mensal_kwh: float | None = None,
    valor_conta_reais: float | None = None,
    endereco: str | None = None,
) -> dict[str, Any]:
    """Calcula uma estimativa preliminar de sistema solar e retorno financeiro."""
    settings, api_client, calculation_service = _runtime()
    resposta = await calcular_sistema_solar_use_case(
        latitude=latitude,
        longitude=longitude,
        consumo_mensal_kwh=consumo_mensal_kwh,
        valor_conta_reais=valor_conta_reais,
        endereco=endereco,
        settings=settings,
        api_client=api_client,
        calculation_service=calculation_service,
    )
    return _serializar_resposta(resposta)


SOLAR_CALCULATOR_TOOLS = (geocodificar_endereco, calcular_sistema_solar)

__all__ = [
    "SOLAR_CALCULATOR_TOOLS",
    "calcular_sistema_solar",
    "geocodificar_endereco",
]
