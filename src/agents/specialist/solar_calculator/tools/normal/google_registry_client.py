"""Cliente do endpoint de solar centralizado no repositório google-registry.

Substitui a chamada direta à Solar API do Google
(`https://solar.googleapis.com/...`) por uma chamada HTTP ao
`google-registry` (`GET /v1/solar/roof-viability`), que concentra a
credencial Google, retry/backoff e tradução de erros em um único serviço.

A geocodificação de endereço continua usando `GoogleApiClient`, pois o
google-registry ainda não expõe esse endpoint (ver `app/api/routers` no
repositório google-registry).
"""

from __future__ import annotations

from typing import Any

import httpx

from ..config import Settings
from .google_client import ExternalServiceError

_SERVICE_NAME = "google-registry (solar)"

# Mapeia o `code` padronizado do google-registry
# (`{"code": "<NomeDaExceptionClass>", "message": str, "details"?: object}`)
# para o `code` já usado internamente por `calculator._error_response`.
_ERROR_CODE_MAP: dict[str, str] = {
    "GoogleNotFoundException": "zero_results",
    "GoogleValidationException": "invalid_payload",
    "GoogleAuthenticationException": "authentication_error",
    "GoogleAuthorizationException": "authentication_error",
    "GoogleRateLimitException": "rate_limited",
    "GoogleTimeoutException": "timeout",
    "GoogleUnavailableException": "network_error",
    "GoogleUpstreamException": "invalid_payload",
}


class GoogleRegistrySolarClient:
    """Consulta a viabilidade solar de uma coordenada via `google-registry`.

    Implementa apenas `fetch_building_insights` do `Protocol` `SolarApiClient`;
    a geocodificação de endereço não é delegada a este cliente porque o
    google-registry ainda não expõe essa capability.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def fetch_building_insights(
        self, latitude: float, longitude: float
    ) -> dict[str, Any]:
        """Consulta `GET /v1/solar/roof-viability` e traduz para o formato
        bruto que `SolarCalculationService.calculate` espera
        (`solarPotential.*`), preservando o mesmo contrato usado pelo
        adapter que chamava a Solar API do Google diretamente.
        """
        timeout = httpx.Timeout(self._settings.request_timeout_seconds)
        params = {"latitude": latitude, "longitude": longitude}
        headers = self._auth_headers()

        try:
            async with httpx.AsyncClient(
                base_url=self._settings.google_registry_url, timeout=timeout
            ) as client:
                response = await client.get(
                    "/v1/solar/roof-viability", params=params, headers=headers
                )
        except httpx.TimeoutException as exc:
            raise ExternalServiceError(
                f"Tempo limite excedido ao consultar {_SERVICE_NAME}.",
                service=_SERVICE_NAME,
                code="timeout",
            ) from exc
        except httpx.RequestError as exc:
            raise ExternalServiceError(
                f"Falha de rede ao consultar {_SERVICE_NAME}.",
                service=_SERVICE_NAME,
                code="network_error",
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise ExternalServiceError(
                f"{_SERVICE_NAME} retornou uma resposta inválida.",
                service=_SERVICE_NAME,
                code="invalid_json",
                status_code=response.status_code,
            ) from exc

        if response.status_code >= 400:
            raise self._error_from_payload(payload, response.status_code)

        if not isinstance(payload, dict):
            raise ExternalServiceError(
                f"{_SERVICE_NAME} retornou um formato inesperado.",
                service=_SERVICE_NAME,
                code="invalid_payload",
                status_code=response.status_code,
            )

        return self._to_building_insights(payload)

    def _auth_headers(self) -> dict[str, str]:
        token = self._settings.google_registry_auth_token
        return {"Authorization": f"Bearer {token}"} if token else {}

    def _error_from_payload(
        self, payload: Any, status_code: int
    ) -> ExternalServiceError:
        error_class_name = None
        message = f"{_SERVICE_NAME} retornou HTTP {status_code}."
        if isinstance(payload, dict):
            error_class_name = payload.get("code")
            message = str(payload.get("message") or message)
        code = _ERROR_CODE_MAP.get(str(error_class_name), "http_error")
        return ExternalServiceError(
            message,
            service=_SERVICE_NAME,
            code=code,
            status_code=status_code,
        )

    @staticmethod
    def _to_building_insights(payload: dict[str, Any]) -> dict[str, Any]:
        """Traduz `SolarViability` (google-registry) para o payload bruto
        `solarPotential` que `SolarCalculationService.calculate` espera.
        """
        solar_potential: dict[str, Any] = {
            "maxArrayAreaMeters2": payload.get("usable_roof_area_m2"),
            "maxArrayPanelsCount": payload.get("max_panel_count"),
            "maxSunshineHoursPerYear": payload.get("annual_sunshine_hours"),
            "carbonOffsetFactorKgPerMwh": payload.get("carbon_offset_factor_kg_mwh"),
        }

        panel_capacity_watts = payload.get("panel_capacity_watts")
        if panel_capacity_watts is not None:
            solar_potential["panelCapacityWatts"] = panel_capacity_watts

        panel_width_meters = payload.get("panel_width_meters")
        if panel_width_meters is not None:
            solar_potential["panelWidthMeters"] = panel_width_meters

        panel_height_meters = payload.get("panel_height_meters")
        if panel_height_meters is not None:
            solar_potential["panelHeightMeters"] = panel_height_meters

        panel_configs = payload.get("panel_configs") or []
        solar_potential["solarPanelConfigs"] = [
            {
                "panelsCount": config.get("panels_count"),
                "yearlyEnergyDcKwh": config.get("yearly_energy_dc_kwh"),
            }
            for config in panel_configs
            if isinstance(config, dict)
        ]

        return {"solarPotential": solar_potential}
