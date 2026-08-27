from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):

    MONGO_URI: str = Field(
        "mongodb://localhost:27017",
        validation_alias=AliasChoices("MONGO_URI", "MONGODB_URI"),
    )

    UPSTASH_REDIS_HOST: str | None = None
    UPSTASH_REDIS_PORT: int = 6379
    UPSTASH_REDIS_USERNAME: str = "default"
    UPSTASH_REDIS_PASSWORD: str | None = None


    API_MESSENGER_URL: str | None = None
    API_MESSENGER_CLIENT_SECRET: str | None = None

    GOOGLE_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
