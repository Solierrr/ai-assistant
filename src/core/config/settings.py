from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    MONGO_URI: str = Field(
        "mongodb://localhost:27017",
        validation_alias=AliasChoices("MONGO_URI", "MONGODB_URI"),
    )
    MONGO_DB: str = "assessor_inteligente"
    CHECKPOINT_TTL_DIAS: int = 30

    UPSTASH_REDIS_HOST: str | None = Field(
        None, validation_alias=AliasChoices("UPSTASH_AGENTS_HOST", "UPSTASH_REDIS_HOST")
    )
    UPSTASH_REDIS_PORT: int = Field(
        6379, validation_alias=AliasChoices("UPSTASH_AGENTS_PORT", "UPSTASH_REDIS_PORT")
    )
    UPSTASH_REDIS_USERNAME: str = Field(
        "default",
        validation_alias=AliasChoices("UPSTASH_AGENTS_USERNAME", "UPSTASH_REDIS_USERNAME"),
    )
    UPSTASH_REDIS_PASSWORD: str | None = Field(
        None,
        validation_alias=AliasChoices("UPSTASH_AGENTS_PASSWORD", "UPSTASH_REDIS_PASSWORD"),
    )
    UPSTASH_AGENTS_HOST: str | None = Field(
        None, validation_alias=AliasChoices("UPSTASH_AGENTS_HOST", "UPSTASH_REDIS_HOST")
    )
    UPSTASH_AGENTS_PORT: int = Field(
        6379, validation_alias=AliasChoices("UPSTASH_AGENTS_PORT", "UPSTASH_REDIS_PORT")
    )
    UPSTASH_AGENTS_USERNAME: str = Field(
        "default",
        validation_alias=AliasChoices("UPSTASH_AGENTS_USERNAME", "UPSTASH_REDIS_USERNAME"),
    )
    UPSTASH_AGENTS_PASSWORD: str | None = Field(
        None,
        validation_alias=AliasChoices("UPSTASH_AGENTS_PASSWORD", "UPSTASH_REDIS_PASSWORD"),
    )

    AGENT_STREAM_CHATBOT: str = "agent:stream:chatbot"
    AGENT_STREAM_MAXLEN: int = Field(default=1_000, gt=0)
    AGENT_STREAM_GROUP: str = "chatbot-agents"
    AGENT_CONSUMER_PREFIX: str = "chatbot-consumer"
    AGENT_CONSUMER_COUNT: int = Field(default=2, ge=1)
    AGENT_CONSUMER_BLOCK_MS: int = Field(default=60_000, gt=0)
    AGENT_CONSUMER_BATCH_SIZE: int = Field(default=1, gt=0)
    AGENT_CONSUMER_CLAIM_BATCH_SIZE: int = Field(default=10, gt=0)
    AGENT_CONSUMER_CLAIM_IDLE_MS: int = Field(default=300_000, gt=0)
    AGENT_CONSUMER_CLAIM_INTERVAL_MS: int = Field(default=300_000, gt=0)
    AGENT_CONSUMER_IDLE_DELAY_MS: int = Field(default=1_000, gt=0)
    AGENT_CONSUMER_RETRY_DELAY_MS: int = Field(default=1_000, gt=0)
    AGENT_CONSUMER_MAX_RETRY_DELAY_MS: int = Field(default=30_000, gt=0)
    AGENT_PROCESSING_TIMEOUT_SECONDS: float = Field(default=50.0, gt=0)
    AGENT_RESULT_PREFIX: str = "agent:result:chatbot"
    AGENT_RESULT_TTL_SECONDS: int = Field(default=900, gt=0)

    API_MESSENGER_URL: str = "http://localhost:8080"
    API_MESSENGER_TIMEOUT_SECONDS: float = Field(default=10.0, gt=0)

    ENVIRONMENT: str = "LOCAL"

    TEST_USER_TOKEN: str | None = None

    MCP_URL: str = "http://localhost:8001/mcp"
    MCP_API_KEY: str | None = None

    GOOGLE_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_TIMEOUT_SECONDS: float = Field(default=12.0, gt=0)
    GEMINI_MAX_RETRIES: int = Field(default=0, ge=0)
    GEMINI_MAX_TOKENS: int = Field(default=2_048, gt=0)
    GEMINI_THINKING_LEVEL: str = "minimal"
    GROQ_FAST_MODEL: str = "openai/gpt-oss-20b"
    GROQ_QUALITY_MODEL: str = "openai/gpt-oss-120b"
    GROQ_TIMEOUT_SECONDS: float = Field(default=8.0, gt=0)
    GROQ_MAX_RETRIES: int = Field(default=0, ge=0)
    GROQ_MAX_TOKENS: int = Field(default=1_024, gt=0)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
