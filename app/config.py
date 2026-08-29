from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application & Environment
    APP_NAME: str = "SurakshaGrid"
    APP_ENV: str = "development"
    DEBUG: bool = False

    # Security & Authentication
    SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    OFFICER_3492_PASSWORD_HASH: str = ""

    # Database Configuration
    DATABASE_URL: str = "sqlite:///./surakshagrid.db"
    POSTGRES_DB: str = "surakshagrid"
    POSTGRES_USER: str = "surakshagrid"
    POSTGRES_PASSWORD: str = "surakshagrid"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    # External Integration Services
    OSRM_BASE_URL: str = "http://localhost:5000"
    ML_MODEL_PATH: str = "ml/models/inundation_model.joblib"
    SAR_RASTER_PATH: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
