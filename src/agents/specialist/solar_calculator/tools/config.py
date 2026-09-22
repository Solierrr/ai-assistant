"""Configuração da calculadora solar, derivada do Settings central do projeto.

As variáveis de ambiente já são carregadas uma única vez por
`src.core.config.settings.settings` (pydantic-settings, lê `.env` na raiz do
projeto). Este módulo só valida os valores específicos da calculadora e
resolve as regras de negócio que dependem de mais de um campo (ex.: exigir
`google_api_key` apenas quando `solar_api_auth_mode == "google_api_key"`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from urllib.parse import urlparse

from src.core.config.settings import settings as app_settings


class ConfigurationError(ValueError):
    """Indica uma configuração ausente ou inválida."""


def _validate_positive_float(name: str, value: float) -> float:
    if not math.isfinite(value) or value <= 0:
        raise ConfigurationError(f"{name} deve ser um número finito maior que zero.")
    return value


def _validate_fraction(name: str, value: float) -> float:
    _validate_positive_float(name, value)
    if value > 1:
        raise ConfigurationError(f"{name} deve estar no intervalo maior que 0 e até 1.")
    return value


def _validate_non_negative_rate(name: str, value: float) -> float:
    if not math.isfinite(value) or not 0 <= value < 1:
        raise ConfigurationError(
            f"{name} deve estar no intervalo de 0 (inclusive) a 1 (exclusive)."
        )
    return value


def _validate_positive_int(name: str, value: int) -> int:
    if value <= 0:
        raise ConfigurationError(f"{name} deve ser maior que zero.")
    return value


def _validate_https_url(name: str, value: str) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or not parsed.hostname or parsed.username:
        raise ConfigurationError(
            f"{name} deve ser uma URL HTTPS válida e sem credenciais embutidas."
        )
    return value.strip()


def _validate_choice(name: str, value: str, allowed: set[str]) -> str:
    normalized = value.strip().lower()
    if normalized not in allowed:
        options = ", ".join(sorted(allowed))
        raise ConfigurationError(f"{name} deve ser um destes valores: {options}.")
    return normalized


@dataclass(frozen=True, slots=True)
class Settings:
    """Parâmetros operacionais e hipóteses financeiras da calculadora."""

    demo_mode: bool
    google_api_key: str
    solar_api_url: str
    solar_api_auth_mode: str
    geocoding_api_url: str
    solar_data_source: str
    google_registry_url: str
    google_registry_auth_token: str | None
    request_timeout_seconds: float
    http_max_attempts: int
    default_tariff_reais_kwh: float
    panel_reference: str
    panel_power_watts: float
    panel_width_meters: float
    panel_height_meters: float
    panel_module_reference_price_reais: float
    installation_labor_cost_per_panel_reais: float
    other_system_cost_per_panel_reais: float
    fallback_panel_monthly_kwh: float
    system_performance_ratio: float
    annual_panel_degradation_rate: float

    @classmethod
    def from_env(cls) -> "Settings":
        """Lê e valida os campos relevantes do Settings central do projeto."""
        solar_api_url = _validate_https_url(
            "SOLAR_API_URL", app_settings.SOLAR_API_URL
        )
        solar_api_auth_mode = _validate_choice(
            "SOLAR_API_AUTH_MODE",
            app_settings.SOLAR_API_AUTH_MODE,
            {"google_api_key", "none"},
        )
        geocoding_api_url = _validate_https_url(
            "GEOCODING_API_URL", app_settings.GEOCODING_API_URL
        )

        if (
            solar_api_auth_mode == "google_api_key"
            and urlparse(solar_api_url).hostname != "solar.googleapis.com"
        ):
            raise ConfigurationError(
                "SOLAR_API_AUTH_MODE=google_api_key só pode ser usado com "
                "solar.googleapis.com. Use 'none' para um endpoint centralizado "
                "compatível ou implemente autenticação própria no adapter."
            )
        if urlparse(geocoding_api_url).hostname != "maps.googleapis.com":
            raise ConfigurationError(
                "GEOCODING_API_URL deve usar maps.googleapis.com para evitar "
                "encaminhar a chave Google a outro host."
            )

        solar_data_source = _validate_choice(
            "SOLAR_DATA_SOURCE",
            app_settings.SOLAR_DATA_SOURCE,
            {"google_direct", "google_registry"},
        )
        google_registry_url = app_settings.GOOGLE_REGISTRY_URL.strip().rstrip("/")
        if solar_data_source == "google_registry":
            parsed_registry_url = urlparse(google_registry_url)
            if parsed_registry_url.scheme not in {"http", "https"} or not parsed_registry_url.hostname:
                raise ConfigurationError(
                    "GOOGLE_REGISTRY_URL deve ser uma URL http(s) válida quando "
                    "SOLAR_DATA_SOURCE=google_registry."
                )

        return cls(
            demo_mode=app_settings.DEMO_MODE,
            google_api_key=(
                app_settings.GOOGLE_SOLAR_API_KEY or app_settings.GOOGLE_API_KEY or ""
            ).strip(),
            solar_api_url=solar_api_url,
            solar_api_auth_mode=solar_api_auth_mode,
            geocoding_api_url=geocoding_api_url,
            solar_data_source=solar_data_source,
            google_registry_url=google_registry_url,
            google_registry_auth_token=(
                app_settings.GOOGLE_REGISTRY_AUTH_TOKEN or None
            ),
            request_timeout_seconds=_validate_positive_float(
                "REQUEST_TIMEOUT_SECONDS", app_settings.REQUEST_TIMEOUT_SECONDS
            ),
            http_max_attempts=_validate_positive_int(
                "HTTP_MAX_ATTEMPTS", app_settings.HTTP_MAX_ATTEMPTS
            ),
            default_tariff_reais_kwh=_validate_positive_float(
                "DEFAULT_TARIFF_REAIS_KWH", app_settings.DEFAULT_TARIFF_REAIS_KWH
            ),
            panel_reference=app_settings.PANEL_REFERENCE.strip()
            or "JA Solar JAM72S30-550/MR",
            panel_power_watts=_validate_positive_float(
                "PANEL_POWER_WATTS", app_settings.PANEL_POWER_WATTS
            ),
            panel_width_meters=_validate_positive_float(
                "PANEL_WIDTH_METERS", app_settings.PANEL_WIDTH_METERS
            ),
            panel_height_meters=_validate_positive_float(
                "PANEL_HEIGHT_METERS", app_settings.PANEL_HEIGHT_METERS
            ),
            panel_module_reference_price_reais=_validate_positive_float(
                "PANEL_MODULE_REFERENCE_PRICE_REAIS",
                app_settings.PANEL_MODULE_REFERENCE_PRICE_REAIS,
            ),
            installation_labor_cost_per_panel_reais=_validate_positive_float(
                "INSTALLATION_LABOR_COST_PER_PANEL_REAIS",
                app_settings.INSTALLATION_LABOR_COST_PER_PANEL_REAIS,
            ),
            other_system_cost_per_panel_reais=_validate_positive_float(
                "OTHER_SYSTEM_COST_PER_PANEL_REAIS",
                app_settings.OTHER_SYSTEM_COST_PER_PANEL_REAIS,
            ),
            fallback_panel_monthly_kwh=_validate_positive_float(
                "FALLBACK_PANEL_MONTHLY_KWH", app_settings.FALLBACK_PANEL_MONTHLY_KWH
            ),
            system_performance_ratio=_validate_fraction(
                "SYSTEM_PERFORMANCE_RATIO", app_settings.SYSTEM_PERFORMANCE_RATIO
            ),
            annual_panel_degradation_rate=_validate_non_negative_rate(
                "ANNUAL_PANEL_DEGRADATION_RATE",
                app_settings.ANNUAL_PANEL_DEGRADATION_RATE,
            ),
        )

    @property
    def estimated_total_cost_per_panel_reais(self) -> float:
        """Soma módulo, mão de obra e demais itens rateados do sistema."""
        return (
            self.panel_module_reference_price_reais
            + self.installation_labor_cost_per_panel_reais
            + self.other_system_cost_per_panel_reais
        )

    def require_google_api_key(self) -> str:
        """Retorna a chave configurada ou falha antes de uma chamada Google."""
        if not self.google_api_key or self.google_api_key == "SUA_CHAVE_AQUI":
            raise ConfigurationError(
                "GOOGLE_SOLAR_API_KEY não foi configurada. "
                "Defina-a no arquivo .env (ou GOOGLE_API_KEY como fallback)."
            )
        return self.google_api_key
