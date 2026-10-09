"""Application settings, loaded from backend/.env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    anthropic_api_key: str = ""
    ai_model: str = "claude-haiku-5-5"
    database_url: str = "sqlite:///./smartbasket.db"
    store_name: str = "Smart Market"
    admin_pin: str = ""

    @property
    def ai_mode(self) -> str:
        """"ai" when an API key is configured, otherwise the offline fallback."""
        return "ai" if self.anthropic_api_key.strip() else "offline"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
