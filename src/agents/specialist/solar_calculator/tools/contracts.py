"""Contratos compartilhados entre os adapters da aplicação."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class GeocodingResult:
    """Coordenadas resolvidas por um adapter real ou demonstrativo."""

    latitude: float
    longitude: float
    formatted_address: str


class SolarApiClient(Protocol):
    """Interface assíncrona que qualquer adapter de dados solares deve seguir.

    Hoje só existem os adapters `GoogleApiClient` (chama a Google direto) e
    `DemoApiClient` (dados fictícios). Quando a API do Google for
    centralizada em outro repositório, um novo adapter que chama esse
    serviço via HTTP pode implementar esta mesma interface sem exigir
    mudanças em `calculator.py` ou `service.py`.
    """

    async def geocode_address(self, address: str) -> GeocodingResult: ...

    async def fetch_building_insights(
        self, latitude: float, longitude: float
    ) -> dict[str, Any]: ...
