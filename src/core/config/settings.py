from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    MONGO_URI: str = Field(
        "mongodb://localhost:27017",
        validation_alias=AliasChoices("MONGO_URI", "MONGODB_URI"),
    )
    CHECKPOINT_TTL_DIAS: int = 30

    UPSTASH_REDIS_HOST: str | None = None
    UPSTASH_REDIS_PORT: int = 6379
    UPSTASH_REDIS_USERNAME: str = "default"
    UPSTASH_REDIS_PASSWORD: str | None = None

    API_MESSENGER_URL: str | None = None

    ENVIRONMENT: str = "LOCAL"

    TEST_USER_TOKEN: str | None = (
        None  # só pra uso local via main.py, nunca em produção
    )

    MCP_URL: str = "http://localhost:8001/mcp"
    MCP_API_KEY: str | None = None

    GOOGLE_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None

    # solar_calculator: hipóteses financeiras e origem dos dados de potencial
    # solar. GOOGLE_SOLAR_API_KEY, quando ausente, cai no GOOGLE_API_KEY geral.
    DEMO_MODE: bool = False
    GOOGLE_SOLAR_API_KEY: str | None = None
    SOLAR_API_URL: str = "https://solar.googleapis.com/v1/buildingInsights:findClosest"
    SOLAR_API_AUTH_MODE: str = "google_api_key"
    GEOCODING_API_URL: str = "https://maps.googleapis.com/maps/api/geocode/json"

    # solar_calculator: fonte dos dados de potencial solar. "google_registry"
    # consulta o serviço centralizado google-registry (GET /v1/solar/roof-viability)
    # em vez de chamar a Solar API do Google diretamente deste projeto.
    SOLAR_DATA_SOURCE: str = "google_direct"
    GOOGLE_REGISTRY_URL: str = "http://localhost:8000"
    GOOGLE_REGISTRY_AUTH_TOKEN: str | None = None
    REQUEST_TIMEOUT_SECONDS: float = 15.0
    HTTP_MAX_ATTEMPTS: int = 3
    DEFAULT_TARIFF_REAIS_KWH: float = 0.95
    PANEL_REFERENCE: str = "JA Solar JAM72S30-550/MR"
    PANEL_POWER_WATTS: float = 550.0
    PANEL_WIDTH_METERS: float = 1.134
    PANEL_HEIGHT_METERS: float = 2.278
    PANEL_MODULE_REFERENCE_PRICE_REAIS: float = 780.0
    INSTALLATION_LABOR_COST_PER_PANEL_REAIS: float = 632.5
    OTHER_SYSTEM_COST_PER_PANEL_REAIS: float = 387.5
    FALLBACK_PANEL_MONTHLY_KWH: float = 65.0
    SYSTEM_PERFORMANCE_RATIO: float = 0.85
    ANNUAL_PANEL_DEGRADATION_RATE: float = 0.0055

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
