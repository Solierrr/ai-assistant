import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.routes import chat
from src.core.config.settings import settings
from src.infra.database.mongo.indexes.create_indexes import create_indexes
from src.infra.database.mongo.mongodb_client import MongoDBClient
from src.infra.messaging.consumer import ensure_consumer_group, run_consumer
from src.infra.messaging.redis_client import close_redis, connect_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    await MongoDBClient.connect()
    await create_indexes()
    await connect_redis()

    stop_event = asyncio.Event()
    consumer_tasks: list[asyncio.Task] = []

    try:
        await ensure_consumer_group()
        consumer_tasks = [
            asyncio.create_task(
                run_consumer(stop_event),
                name=f"chatbot-consumer-{index + 1}",
            )
            for index in range(settings.AGENT_CONSUMER_COUNT)
        ]
        app.state.consumer_tasks = consumer_tasks
        yield
    finally:
        stop_event.set()
        for task in consumer_tasks:
            task.cancel()
        await asyncio.gather(*consumer_tasks, return_exceptions=True)
        await close_redis()


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
    if not settings.UPSTASH_REDIS_HOST:
        missing.append("UPSTASH_REDIS_HOST")
    if not settings.UPSTASH_REDIS_PASSWORD:
        missing.append("UPSTASH_REDIS_PASSWORD")

    return {
        "status": "ok" if not missing else "atencao",
        "missing_settings": missing,
    }
