from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    MONGO_URI: str = Field(
        "mongodb://localhost:27017",
        validation_alias=AliasChoices("MONGO_URI", "MONGODB_URI"),
    )

    API_MESSENGER_URL: str
    API_MESSENGER_CLIENT_SECRET: str

    GOOGLE_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
