import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.a2a.server import mount as mount_a2a
from src.api.routes import chat
from src.core.llm.keys import key_client
from src.core.observability.langsmith_tracing import warn_if_global_tracing
from src.infra.database.mongo.indexes.user_memory_indexes import (
    ensure_user_memory_indexes,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    warn_if_global_tracing()
    await ensure_user_memory_indexes()
    yield


app = FastAPI(
    title="Solaria API",
    description="Marketplace B2B do setor fotovoltaico — API do assistente de IA.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000,http://localhost:5174,http://127.0.0.1:5174,https://web-sandbox-7ug0.onrender.com").split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(chat.router)
mount_a2a(app)


@app.get("/health")
def health() -> dict:
    """Responde 'ok' se o servidor subiu, listando configuração ausente."""
    configured = key_client().providers()
    missing = [
        f"{provider.upper()}_API_KEY"
        for provider in ("gemini", "groq")
        if provider not in configured
    ]

    return {
        "status": "ok" if not missing else "atencao",
        "missing_settings": missing,
    }
