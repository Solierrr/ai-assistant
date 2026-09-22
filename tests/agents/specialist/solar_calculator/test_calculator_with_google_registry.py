"""Teste de integração: calcular_sistema_solar_use_case ponta a ponta usando
o adapter que consulta o google-registry no lugar da Solar API direta."""

import httpx
import pytest
import respx

from src.agents.specialist.solar_calculator.tools.calculator import (
    calcular_sistema_solar_use_case,
)
from src.agents.specialist.solar_calculator.tools.config import Settings
from src.agents.specialist.solar_calculator.tools.normal.google_registry_client import (
    GoogleRegistrySolarClient,
)
from src.agents.specialist.solar_calculator.tools.service import (
    SolarCalculationService,
)


def _settings() -> Settings:
    return Settings(
        demo_mode=False,
        google_api_key="fake-key",
        solar_api_url="https://solar.googleapis.com/v1/buildingInsights:findClosest",
        solar_api_auth_mode="google_api_key",
        geocoding_api_url="https://maps.googleapis.com/maps/api/geocode/json",
        solar_data_source="google_registry",
        google_registry_url="http://google-registry.test",
        google_registry_auth_token="fake-token",
        request_timeout_seconds=5.0,
        http_max_attempts=3,
        default_tariff_reais_kwh=0.95,
        panel_reference="JA Solar JAM72S30-550/MR",
        panel_power_watts=550.0,
        panel_width_meters=1.134,
        panel_height_meters=2.278,
        panel_module_reference_price_reais=780.0,
        installation_labor_cost_per_panel_reais=632.5,
        other_system_cost_per_panel_reais=387.5,
        fallback_panel_monthly_kwh=65.0,
        system_performance_ratio=0.85,
        annual_panel_degradation_rate=0.0055,
    )


@pytest.mark.asyncio
@respx.mock
async def test_calcular_sistema_solar_use_case_uses_google_registry_panel_configs():
    respx.get("http://google-registry.test/v1/solar/roof-viability").mock(
        return_value=httpx.Response(
            200,
            json={
                "imagery_date": "2024-03-15",
                "usable_roof_area_m2": 100.0,
                "max_panel_count": 20,
                "annual_sunshine_hours": 1800.0,
                "carbon_offset_factor_kg_mwh": 400.0,
                "roof_segments": [],
                "panel_capacity_watts": 400.0,
                "panel_width_meters": 1.045,
                "panel_height_meters": 1.879,
                "panel_configs": [
                    {"panels_count": 4, "yearly_energy_dc_kwh": 1800.0},
                    {"panels_count": 8, "yearly_energy_dc_kwh": 3600.0},
                    {"panels_count": 12, "yearly_energy_dc_kwh": 5400.0},
                ],
            },
        )
    )

    settings = _settings()
    api_client = GoogleRegistrySolarClient(settings)
    calculation_service = SolarCalculationService(settings)

    response = await calcular_sistema_solar_use_case(
        latitude=-23.5614,
        longitude=-46.6559,
        consumo_mensal_kwh=500.0,
        valor_conta_reais=None,
        endereco=None,
        settings=settings,
        api_client=api_client,
        calculation_service=calculation_service,
    )

    payload = response.model_dump(mode="json")
    assert payload["sucesso"] is True
    assert payload["modo_execucao"] == "google_apis"
    # A config Google usada deve refletir o painel de referência retornado
    # pelo google-registry (400W), não o painel local configurado (550W).
    assert payload["fonte_produtividade"] == (
        "configuracao_google_ajustada_para_potencia_e_desempenho"
    )
    assert payload["paineis_recomendados"] > 0
    assert payload["investimento_estimado_reais"] > 0


@pytest.mark.asyncio
@respx.mock
async def test_calcular_sistema_solar_use_case_reports_not_found_as_domain_error():
    respx.get("http://google-registry.test/v1/solar/roof-viability").mock(
        return_value=httpx.Response(
            404,
            json={"code": "GoogleNotFoundException", "message": "Sem dados para região solicitada"},
        )
    )

    settings = _settings()
    api_client = GoogleRegistrySolarClient(settings)
    calculation_service = SolarCalculationService(settings)

    response = await calcular_sistema_solar_use_case(
        latitude=-23.5614,
        longitude=-46.6559,
        consumo_mensal_kwh=500.0,
        valor_conta_reais=None,
        endereco=None,
        settings=settings,
        api_client=api_client,
        calculation_service=calculation_service,
    )

    payload = response.model_dump(mode="json")
    assert payload["sucesso"] is False
    assert payload["erro"]["codigo"] == "zero_results"
