import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.routes import chat
from src.core.config.settings import settings
from src.core.llm.llm_gemini import llm_gemini
from src.core.llm.llm_groq import llm_groq
from src.infra.api_messenger.client import close_api_messenger_client
from src.infra.database.mongo.indexes.create_indexes import create_indexes
from src.infra.database.mongo.mongodb_client import MongoDBClient
from src.infra.messaging.consumer import ensure_consumer_group, run_consumer
from src.infra.messaging.redis_client import close_redis, connect_redis
from src.infra.privacy.core_redis_client import close_core_redis, connect_core_redis
from src.infra.privacy.pii_map_store import validate_pii_encryption_key

logger = logging.getLogger(__name__)


def warm_llm_clients() -> None:
    llm_gemini()
    llm_groq()
    logger.info("Clientes LLM preparados")


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event = asyncio.Event()
    consumer_tasks: list[asyncio.Task] = []

    try:
        await MongoDBClient.connect()
        await create_indexes()
        validate_pii_encryption_key()
        await connect_redis()
        await connect_core_redis()
        await ensure_consumer_group()
        warm_llm_clients()
        consumer_tasks = [
            asyncio.create_task(
                run_consumer(stop_event, recover_pending=index == 0),
                name=f"chatbot-consumer-{index + 1}",
            )
            for index in range(settings.AGENT_CONSUMER_COUNT)
        ]
        app.state.consumer_tasks = consumer_tasks
        logger.info("Consumers do chatbot iniciados: %s", settings.AGENT_CONSUMER_COUNT)
        yield
    finally:
        stop_event.set()
        for task in consumer_tasks:
            task.cancel()
        await asyncio.gather(*consumer_tasks, return_exceptions=True)
        if consumer_tasks:
            logger.info("Consumers do chatbot encerrados")
        await close_api_messenger_client()
        await close_core_redis()
        await close_redis()


app = FastAPI(
    title="Solaria API",
    description="Marketplace B2B do setor fotovoltaico - API do assistente de IA.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(chat.router)


@app.get("/health")
def health() -> dict:
    """Informa se as configurações obrigatórias foram fornecidas."""
    required_settings = {
        "GOOGLE_API_KEY": settings.GOOGLE_API_KEY,
        "GROQ_API_KEY": settings.GROQ_API_KEY,
        "UPSTASH_AGENTS_HOST": settings.UPSTASH_AGENTS_HOST,
        "UPSTASH_AGENTS_PASSWORD": settings.UPSTASH_AGENTS_PASSWORD,
        "UPSTASH_CORE_HOST": settings.UPSTASH_CORE_HOST,
        "UPSTASH_CORE_PASSWORD": settings.UPSTASH_CORE_PASSWORD,
        "PII_ENCRYPTION_KEY": settings.PII_ENCRYPTION_KEY,
    }
    missing = [name for name, value in required_settings.items() if not value]
    return {
        "status": "ok" if not missing else "atencao",
        "missing_settings": missing,
    }
