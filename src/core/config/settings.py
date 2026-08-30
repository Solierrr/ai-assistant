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

    GOOGLE_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
