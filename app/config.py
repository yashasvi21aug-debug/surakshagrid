from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "SurakshaGrid"
    APP_ENV: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"

    DATABASE_URL: str = "postgresql+asyncpg://surakshagrid:surakshagrid@localhost:5432/surakshagrid"
    POSTGRES_DB: str = "surakshagrid"
    POSTGRES_USER: str = "surakshagrid"
    POSTGRES_PASSWORD: str = "surakshagrid"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
