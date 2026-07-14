from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):

    MONGO_URI: str = Field(
        "mongodb://localhost:27017",
        validation_alias=AliasChoices("MONGO_URI", "MONGODB_URI"),
    )

    MONGO_DB: str = "assessor_inteligente"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
