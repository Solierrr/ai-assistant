from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from src.a2a.server import mount as mount_a2a
from src.api.errors import register_error_handlers
from src.api.routes import chat, debug, health
from src.api.schemas.problem import ProblemDetail
from src.core.config.settings import settings
from src.core.observability.langsmith_tracing import warn_if_global_tracing
from src.infra.database.mongo.indexes.user_memory_indexes import (
    ensure_user_memory_indexes,
)
from src.version import VERSION

PROBLEM_REF = f"#/components/schemas/{ProblemDetail.__name__}"
A2A_PATHS = frozenset({"/a2a", "/.well-known/agent-card.json"})


def cors_origins(raw: str) -> list[str]:
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    warn_if_global_tracing()
    await ensure_user_memory_indexes()
    yield


app = FastAPI(
    title="Solaria — ai-assistant",
    description=(
        "Assistente virtual da plataforma para quem procura soluções de energia "
        "solar: conversa com a pessoa, identifica a necessidade e ajuda a encontrar "
        "placas solares, itens de fixação, profissionais e empresas adequados a cada "
        "caso. Autentique com o JWT emitido pelo api-auth (bearerAuth). O protocolo "
        "A2A (Agent Card em /.well-known/agent-card.json e JSON-RPC em /a2a) não faz "
        "parte deste contrato."
    ),
    version=VERSION,
    contact={"name": "Solaria", "url": "https://github.com/Solierrr"},
    license_info={
        "name": "CC0-1.0",
        "url": "https://creativecommons.org/publicdomain/zero/1.0/",
    },
    servers=[
        {"url": "https://ai-assistant-5ljd.onrender.com", "description": "QA"},
        {"url": "http://localhost:8000", "description": "Local"},
    ],
    openapi_tags=[
        {"name": "Conversa", "description": "Turnos de conversa com o assistente."},
        {"name": "Saúde", "description": "Estado do processo e das dependências."},
    ],
    docs_url="/docs" if settings.DOCS_ENABLED else None,
    openapi_url="/openapi.json" if settings.DOCS_ENABLED else None,
    redoc_url=None,
    swagger_ui_parameters={
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "tryItOutEnabled": True,
        "tagsSorter": "alpha",
        "operationsSorter": "alpha",
    },
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(settings.CORS_ALLOWED_ORIGINS),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

register_error_handlers(app)
app.include_router(chat.router)
app.include_router(debug.router)
app.include_router(health.router)
mount_a2a(app)


def build_openapi() -> dict:
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=[
            route
            for route in app.routes
            if getattr(route, "path", None) not in A2A_PATHS
        ],
        tags=app.openapi_tags,
        servers=app.servers,
        contact=app.contact,
        license_info=app.license_info,
    )
    schemas = schema.setdefault("components", {}).setdefault("schemas", {})
    for name in ("HTTPValidationError", "ValidationError"):
        schemas.pop(name, None)
    problem_schema = ProblemDetail.model_json_schema(
        ref_template="#/components/schemas/{model}"
    )
    schemas.update(problem_schema.pop("$defs", {}))
    schemas[ProblemDetail.__name__] = problem_schema
    for path in schema["paths"].values():
        for operation in path.values():
            responses = operation["responses"]
            responses.setdefault("500", {"description": "Erro interno inesperado"})
            for code, response in responses.items():
                if code.startswith(("4", "5")):
                    response["content"] = {
                        "application/problem+json": {"schema": {"$ref": PROBLEM_REF}}
                    }
    schema["security"] = [{"bearerAuth": []}]
    return schema


def openapi() -> dict:
    if app.openapi_schema is None:
        app.openapi_schema = build_openapi()
    return app.openapi_schema


app.openapi = openapi
