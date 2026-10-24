from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    MONGO_URI: str = Field(
        "mongodb://localhost:27017",
        validation_alias=AliasChoices("DB_MONGO_URI", "MONGO_URI", "MONGODB_URI"),
    )
    DB_MONGO_AGENTS: str = "dbagents"
    CHECKPOINT_TTL_DIAS: int = 30

    @field_validator("MONGO_URI", mode="before")
    @classmethod
    def normalize_mongo_uri(cls, value):
        if isinstance(value, str) and value and "://" not in value:
            return f"mongodb+srv://{value}"
        return value

    API_MESSENGER_URL: str | None = None

    JWT_JWKS_URL: str | None = None
    JWT_ISSUER: str | None = None

    ENVIRONMENT: str = "LOCAL"

    # api-core: o assistente lê as unidades do usuário, com o JWT dele, para as
    # recomendações por proximidade.
    API_CORE_URL: str = "http://localhost:8080/api"

    # A2A: URL pública deste serviço (vai no Agent Card) e a do ai-operational,
    # para onde o assistente delega ações do SaaS.
    A2A_PUBLIC_URL: str = "http://localhost:8000"
    A2A_OPERATIONAL_URL: str = "http://localhost:8003"

    TEST_USER_TOKEN: str | None = (
        None  # só pra uso local via main.py, nunca em produção
    )

    MCP_URL: str = "http://localhost:8001/mcp"
    MCP_API_KEY: str | None = None

    QDRANT_URL: str | None = None
    QDRANT_API_KEY: str | None = None

    SOLARIA_LANGSMITH_ENABLED: bool = False
    SOLARIA_LANGSMITH_API_KEY: str | None = None
    SOLARIA_LANGSMITH_PROJECT: str = "solaria-local"
    SOLARIA_LANGSMITH_ENDPOINT: str | None = None
    SOLARIA_LANGSMITH_SAMPLING_RATE: float = 1.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
