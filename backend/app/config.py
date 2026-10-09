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

    @property
    def resolved_database_url(self) -> str:
        """The URL to actually connect with.

        A hosting provider can hand us an env var that exists but is empty —
        a mistyped `vercel env add` does exactly that. Without this guard the
        engine is built from "" and the whole API fails to import, with an
        error that says nothing about the real cause.
        """
        url = (self.database_url or "").strip().strip('"').strip("'")
        if not url:
            print("[config] DATABASE_URL is empty — falling back to local SQLite")
            return "sqlite:///./smartbasket.db"
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
