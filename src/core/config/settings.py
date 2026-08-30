from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    MONGO_URI: str = Field(
        "mongodb://localhost:27017",
        validation_alias=AliasChoices("MONGO_URI", "MONGODB_URI"),
    )
    MONGO_DB: str = "assessor_inteligente"

    UPSTASH_REDIS_HOST: str | None = None
    UPSTASH_REDIS_PORT: int = 6379
    UPSTASH_REDIS_USERNAME: str = "default"
    UPSTASH_REDIS_PASSWORD: str | None = None

    AGENT_STREAM_CHATBOT: str = "agent:stream:chatbot"
    AGENT_STREAM_MAXLEN: int = Field(default=10_000, gt=0)
    AGENT_STREAM_GROUP: str = "chatbot-agents"

    AGENT_CONSUMER_PREFIX: str = "chatbot-consumer"
    AGENT_CONSUMER_BLOCK_MS: int = Field(default=5_000, gt=0)
    AGENT_CONSUMER_BATCH_SIZE: int = Field(default=1, gt=0)
    AGENT_CONSUMER_CLAIM_IDLE_MS: int = Field(default=60_000, gt=0)
    AGENT_CONSUMER_COUNT: int = Field(default=2, ge=1)
    AGENT_CONSUMER_RETRY_DELAY_MS: int = Field(default=1_000, gt=0)

    AGENT_RESULT_PREFIX: str = "agent:result:chatbot"
    AGENT_RESULT_TTL_SECONDS: int = Field(default=900, gt=0)

    GOOGLE_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
