import httpx
import pytest
import respx

from src.agents.specialist.solar_calculator.tools.config import Settings
from src.agents.specialist.solar_calculator.tools.normal.google_client import (
    ExternalServiceError,
)
from src.agents.specialist.solar_calculator.tools.normal.google_registry_client import (
    GoogleRegistrySolarClient,
)


def _settings(**overrides) -> Settings:
    base = {
        "demo_mode": False,
        "google_api_key": "fake-key",
        "solar_api_url": "https://solar.googleapis.com/v1/buildingInsights:findClosest",
        "solar_api_auth_mode": "google_api_key",
        "geocoding_api_url": "https://maps.googleapis.com/maps/api/geocode/json",
        "solar_data_source": "google_registry",
        "google_registry_url": "http://google-registry.test",
        "google_registry_auth_token": "fake-token",
        "request_timeout_seconds": 5.0,
        "http_max_attempts": 3,
        "default_tariff_reais_kwh": 0.95,
        "panel_reference": "Painel Teste",
        "panel_power_watts": 550.0,
        "panel_width_meters": 1.134,
        "panel_height_meters": 2.278,
        "panel_module_reference_price_reais": 780.0,
        "installation_labor_cost_per_panel_reais": 632.5,
        "other_system_cost_per_panel_reais": 387.5,
        "fallback_panel_monthly_kwh": 65.0,
        "system_performance_ratio": 0.85,
        "annual_panel_degradation_rate": 0.0055,
    }
    base.update(overrides)
    return Settings(**base)


@pytest.mark.asyncio
@respx.mock
async def test_fetch_building_insights_translates_success_payload():
    respx.get("http://google-registry.test/v1/solar/roof-viability").mock(
        return_value=httpx.Response(
            200,
            json={
                "imagery_date": "2024-03-15",
                "usable_roof_area_m2": 42.5,
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
                ],
            },
        )
    )

    client = GoogleRegistrySolarClient(_settings())
    result = await client.fetch_building_insights(-23.5614, -46.6559)

    solar_potential = result["solarPotential"]
    assert solar_potential["maxArrayPanelsCount"] == 20
    assert solar_potential["maxSunshineHoursPerYear"] == 1800.0
    assert solar_potential["panelCapacityWatts"] == 400.0
    assert solar_potential["panelWidthMeters"] == 1.045
    assert solar_potential["panelHeightMeters"] == 1.879
    assert solar_potential["solarPanelConfigs"] == [
        {"panelsCount": 4, "yearlyEnergyDcKwh": 1800.0},
        {"panelsCount": 8, "yearlyEnergyDcKwh": 3600.0},
    ]


@pytest.mark.asyncio
@respx.mock
async def test_fetch_building_insights_omits_absent_panel_reference_fields():
    respx.get("http://google-registry.test/v1/solar/roof-viability").mock(
        return_value=httpx.Response(
            200,
            json={
                "imagery_date": "2024-03-15",
                "usable_roof_area_m2": 42.5,
                "max_panel_count": 20,
                "annual_sunshine_hours": 1800.0,
                "carbon_offset_factor_kg_mwh": 400.0,
                "roof_segments": [],
                "panel_configs": [],
            },
        )
    )

    client = GoogleRegistrySolarClient(_settings())
    result = await client.fetch_building_insights(-23.5614, -46.6559)

    solar_potential = result["solarPotential"]
    assert "panelCapacityWatts" not in solar_potential
    assert "panelWidthMeters" not in solar_potential
    assert "panelHeightMeters" not in solar_potential
    assert solar_potential["solarPanelConfigs"] == []


@pytest.mark.asyncio
@respx.mock
async def test_fetch_building_insights_sends_bearer_token():
    route = respx.get("http://google-registry.test/v1/solar/roof-viability").mock(
        return_value=httpx.Response(
            200,
            json={
                "imagery_date": "2024-03-15",
                "usable_roof_area_m2": 42.5,
                "max_panel_count": 20,
                "annual_sunshine_hours": 1800.0,
                "carbon_offset_factor_kg_mwh": 400.0,
                "roof_segments": [],
                "panel_configs": [],
            },
        )
    )

    client = GoogleRegistrySolarClient(_settings())
    await client.fetch_building_insights(-23.5614, -46.6559)

    assert route.calls.last.request.headers["authorization"] == "Bearer fake-token"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_building_insights_maps_not_found_error():
    respx.get("http://google-registry.test/v1/solar/roof-viability").mock(
        return_value=httpx.Response(
            404,
            json={"code": "GoogleNotFoundException", "message": "Sem dados para região solicitada"},
        )
    )

    client = GoogleRegistrySolarClient(_settings())

    with pytest.raises(ExternalServiceError) as exc_info:
        await client.fetch_building_insights(-23.5614, -46.6559)

    assert exc_info.value.code == "zero_results"
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
@respx.mock
async def test_fetch_building_insights_maps_unmapped_error_code():
    respx.get("http://google-registry.test/v1/solar/roof-viability").mock(
        return_value=httpx.Response(500, json={"code": "InternalError", "message": "falha"})
    )

    client = GoogleRegistrySolarClient(_settings())

    with pytest.raises(ExternalServiceError) as exc_info:
        await client.fetch_building_insights(-23.5614, -46.6559)

    assert exc_info.value.code == "http_error"
    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
@respx.mock
async def test_fetch_building_insights_raises_on_timeout():
    respx.get("http://google-registry.test/v1/solar/roof-viability").mock(
        side_effect=httpx.TimeoutException("timed out")
    )

    client = GoogleRegistrySolarClient(_settings())

    with pytest.raises(ExternalServiceError) as exc_info:
        await client.fetch_building_insights(-23.5614, -46.6559)

    assert exc_info.value.code == "timeout"


@pytest.mark.asyncio
async def test_fetch_building_insights_without_token_sends_no_authorization_header():
    with respx.mock(base_url="http://no-token.test") as router:
        router.get("/v1/solar/roof-viability").mock(
            return_value=httpx.Response(
                200,
                json={
                    "imagery_date": "2024-03-15",
                    "usable_roof_area_m2": 42.5,
                    "max_panel_count": 20,
                    "annual_sunshine_hours": 1800.0,
                    "carbon_offset_factor_kg_mwh": 400.0,
                    "roof_segments": [],
                    "panel_configs": [],
                },
            )
        )

        client = GoogleRegistrySolarClient(
            _settings(
                google_registry_url="http://no-token.test",
                google_registry_auth_token=None,
            )
        )
        await client.fetch_building_insights(-23.5614, -46.6559)

        assert "authorization" not in router.calls.last.request.headers
