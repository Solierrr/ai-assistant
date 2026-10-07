from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    MONGO_URI: str = Field(
        "mongodb://localhost:27017",
        validation_alias=AliasChoices("DB_MONGO_URI", "MONGO_URI", "MONGODB_URI"),
    )
    CHECKPOINT_TTL_DIAS: int = 30

    @field_validator("MONGO_URI", mode="before")
    @classmethod
    def normalize_mongo_uri(cls, value):
        if isinstance(value, str) and value and "://" not in value:
            return f"mongodb+srv://{value}"
        return value

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

    API_MESSENGER_URL: str | None = None

    JWT_JWKS_URL: str | None = None
    JWT_ISSUER: str | None = None

    ENVIRONMENT: str = "LOCAL"

    TEST_USER_TOKEN: str | None = (
        None  # só pra uso local via main.py, nunca em produção
    )

    MCP_URL: str = "http://localhost:8001/mcp"
    MCP_API_KEY: str | None = None

    GOOGLE_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None

    QDRANT_URL: str | None = None
    QDRANT_API_KEY: str | None = None


    SOLARIA_LANGSMITH_ENABLED: bool = False
    SOLARIA_LANGSMITH_API_KEY: str | None = None
    SOLARIA_LANGSMITH_PROJECT: str = "solaria-local"
    SOLARIA_LANGSMITH_ENDPOINT: str | None = None
    SOLARIA_LANGSMITH_SAMPLING_RATE: float = 1.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
