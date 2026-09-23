"""Casos de uso da calculadora solar, independentes do adapter de dados usado."""

from __future__ import annotations

import logging
from typing import Any

from .api_models import (
    BrazilianAddressInput,
    GeocodingToolResponse,
    LatitudeInput,
    LongitudeInput,
    MonthlyBillInput,
    MonthlyConsumptionInput,
    OptionalBrazilianAddressInput,
    SolarCalculationToolResponse,
)
from .config import ConfigurationError, Settings
from .contracts import GeocodingResult, SolarApiClient
from .normal.google_client import ExternalServiceError
from .service import InputValidationError, SolarCalculationService, SolarDataError

logger = logging.getLogger(__name__)


async def geocodificar_endereco_use_case(
    endereco: BrazilianAddressInput,
    *,
    settings: Settings,
    api_client: SolarApiClient,
) -> GeocodingToolResponse:
    """Executa a geocodificação isolada da tool LangChain que a expõe."""
    try:
        normalized_address = _validate_address(endereco)
        result = await api_client.geocode_address(normalized_address)
        return GeocodingToolResponse.model_validate(
            {
                "sucesso": True,
                **_execution_metadata(settings),
                "endereco_formatado": result.formatted_address,
                "latitude": round(result.latitude, 7),
                "longitude": round(result.longitude, 7),
            }
        )
    except (InputValidationError, ConfigurationError, ExternalServiceError) as exc:
        return GeocodingToolResponse.model_validate(_error_response(exc, settings))
    except Exception:
        logger.exception("Erro inesperado na geocodificação.")
        return GeocodingToolResponse.model_validate(
            _unexpected_error_response(settings)
        )


async def calcular_sistema_solar_use_case(
    latitude: LatitudeInput = None,
    longitude: LongitudeInput = None,
    consumo_mensal_kwh: MonthlyConsumptionInput = None,
    valor_conta_reais: MonthlyBillInput = None,
    endereco: OptionalBrazilianAddressInput = None,
    *,
    settings: Settings,
    api_client: SolarApiClient,
    calculation_service: SolarCalculationService,
) -> SolarCalculationToolResponse:
    """Executa o cálculo solar isolado da tool LangChain que o expõe."""
    try:
        resolved_latitude, resolved_longitude, geocoding = await _resolve_location(
            latitude=latitude,
            longitude=longitude,
            endereco=endereco,
            calculation_service=calculation_service,
            api_client=api_client,
        )

        calculation_service.resolve_energy_demand(consumo_mensal_kwh, valor_conta_reais)
        building_insights = await api_client.fetch_building_insights(
            resolved_latitude, resolved_longitude
        )
        result = calculation_service.calculate(
            latitude=resolved_latitude,
            longitude=resolved_longitude,
            consumo_mensal_kwh=consumo_mensal_kwh,
            valor_conta_reais=valor_conta_reais,
            building_insights=building_insights,
        )

        if settings.demo_mode:
            result["fonte_produtividade"] = "dados_ficticios_modo_demonstracao"
            result["metodo_capacidade_telhado"] = "dados_ficticios_modo_demonstracao"
            result["configuracao_google_paineis"] = None
            result["potencia_painel_referencia_google_w"] = None
            result["capacidade_google_paineis_referencia"] = None
            result["observacoes"] = [
                observation
                for observation in result["observacoes"]
                if "energia DC da API" not in observation
            ]
            result["observacoes"].insert(
                0,
                "MODO DEMONSTRAÇÃO: localização, telhado e produção solar são fictícios.",
            )

        response: dict[str, Any] = {
            "sucesso": True,
            **_execution_metadata(settings),
            **result,
        }
        if geocoding is not None:
            response["endereco_geocodificado"] = geocoding.formatted_address
        return SolarCalculationToolResponse.model_validate(response)
    except (
        InputValidationError,
        SolarDataError,
        ConfigurationError,
        ExternalServiceError,
    ) as exc:
        return SolarCalculationToolResponse.model_validate(
            _error_response(exc, settings)
        )
    except Exception:
        logger.exception("Erro inesperado no cálculo solar.")
        return SolarCalculationToolResponse.model_validate(
            _unexpected_error_response(settings)
        )


async def _resolve_location(
    *,
    latitude: float | None,
    longitude: float | None,
    endereco: str | None,
    calculation_service: SolarCalculationService,
    api_client: SolarApiClient,
) -> tuple[float, float, GeocodingResult | None]:
    has_any_coordinate = latitude is not None or longitude is not None
    has_address = endereco is not None and bool(endereco.strip())

    if has_any_coordinate and has_address:
        raise InputValidationError(
            "Informe latitude/longitude ou endereco, não os dois formatos juntos."
        )

    if has_any_coordinate:
        if latitude is None or longitude is None:
            raise InputValidationError(
                "latitude e longitude devem ser informadas juntas."
            )
        validated = calculation_service.validate_location(latitude, longitude)
        return validated[0], validated[1], None

    if has_address:
        result = await api_client.geocode_address(_validate_address(endereco))
        validated = calculation_service.validate_location(
            result.latitude, result.longitude
        )
        return validated[0], validated[1], result

    raise InputValidationError(
        "Informe latitude e longitude ou um endereço para localizar o imóvel."
    )


def _execution_metadata(settings: Settings) -> dict[str, Any]:
    if settings.demo_mode:
        return {
            "modo_execucao": "demonstracao_offline",
            "aviso_demonstracao": (
                "Nenhuma API externa foi consultada; localização e potencial "
                "solar são fictícios e servem apenas para testar o software."
            ),
        }
    return {"modo_execucao": "google_apis"}


def _validate_address(address: str | None) -> str:
    if not isinstance(address, str):
        raise InputValidationError("endereco deve ser um texto.")
    normalized = " ".join(address.split())
    if len(normalized) < 5:
        raise InputValidationError("endereco deve ter ao menos 5 caracteres.")
    if len(normalized) > 500:
        raise InputValidationError("endereco deve ter no máximo 500 caracteres.")
    return normalized


def _error_response(exc: Exception, settings: Settings) -> dict[str, Any]:
    if isinstance(exc, InputValidationError):
        code = "entrada_invalida"
    elif isinstance(exc, SolarDataError):
        code = "dados_solares_indisponiveis"
    elif isinstance(exc, ConfigurationError):
        code = "configuracao_invalida"
    elif isinstance(exc, ExternalServiceError):
        code = exc.code
    else:
        code = "erro"

    error: dict[str, Any] = {
        "codigo": code,
        "mensagem": str(exc),
    }
    if isinstance(exc, ExternalServiceError):
        error["servico"] = exc.service
        if exc.status_code is not None:
            error["status_code"] = exc.status_code
    return {
        "sucesso": False,
        **_execution_metadata(settings),
        "erro": error,
    }


def _unexpected_error_response(settings: Settings) -> dict[str, Any]:
    return {
        "sucesso": False,
        **_execution_metadata(settings),
        "erro": {
            "codigo": "erro_interno",
            "mensagem": "Ocorreu um erro interno inesperado na calculadora solar.",
        },
    }
