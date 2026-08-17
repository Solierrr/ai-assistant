from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.routes import chat
from src.core.config.settings import settings
from src.infra.database.mongo.indexes.create_indexes import create_indexes
from src.infra.database.mongo.mongodb_client import MongoDBClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    await MongoDBClient.connect()
    await create_indexes()
    yield


app = FastAPI(
    title="Solaria API",
    description="Marketplace B2B do setor fotovoltaico — API do assistente de IA.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(chat.router)


@app.get("/health")
def health() -> dict:
    """Responde 'ok' se o servidor subiu, listando configuração ausente."""
    missing = []
    if not settings.GOOGLE_API_KEY:
        missing.append("GOOGLE_API_KEY")
    if not settings.GROQ_API_KEY:
        missing.append("GROQ_API_KEY")

    return {
        "status": "ok" if not missing else "atencao",
        "missing_settings": missing,
    }
