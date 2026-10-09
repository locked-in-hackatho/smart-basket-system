"""Application settings, loaded from backend/.env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str = "sqlite:///./smartbasket.db"
    store_name: str = "Smart Market"
    admin_pin: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
