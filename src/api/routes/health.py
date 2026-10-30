import asyncio

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.infra.database.mongo.async_client import get_async_mongodb_client
from src.version import VERSION

router = APIRouter(tags=["Saúde"])

READY_TIMEOUT_SECONDS = 2


class HealthStatus(BaseModel):
    status: str = Field(..., examples=["UP"])
    version: str | None = Field(default=None, examples=["3.1.2"])


async def ping_mongo() -> None:
    await get_async_mongodb_client()["assessor_inteligente"].command("ping")


@router.get(
    "/health",
    response_model=HealthStatus,
    response_model_exclude_none=True,
    operation_id="getHealth",
    summary="Indica se o processo está vivo",
    description="Responde UP com a versão do release, sem consultar dependências.",
    openapi_extra={"security": [], "x-error-codes": ["INTERNAL_ERROR"]},
)
async def health() -> HealthStatus:
    return HealthStatus(status="UP", version=VERSION)


@router.get(
    "/ready",
    response_model=HealthStatus,
    response_model_exclude_none=True,
    operation_id="getReady",
    summary="Indica se o serviço está pronto para atender",
    description=(
        "Confere o MongoDB (checkpointer da conversa e memória de longo prazo). "
        "Responde 503 com status DOWN quando ele não responde em 2 segundos. "
        "Os provedores de LLM ficam de fora porque há fallback entre eles."
    ),
    openapi_extra={"security": [], "x-error-codes": ["INTERNAL_ERROR"]},
)
async def ready():
    try:
        await asyncio.wait_for(ping_mongo(), timeout=READY_TIMEOUT_SECONDS)
    except Exception:  # noqa: BLE001
        return JSONResponse({"status": "DOWN"}, status_code=503)
    return HealthStatus(status="UP")
