"""Application settings, loaded from backend/.env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # The assistant works with either provider, or with neither.
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    ai_model: str = "claude-haiku-5-5"
    ai_provider: str = "auto"  # "auto" | "openai" | "anthropic" | "offline"

    database_url: str = "sqlite:///./smartbasket.db"
    store_name: str = "Smart Market"
    admin_pin: str = ""

    @property
    def provider(self) -> str:
        """Which backend actually answers: "openai", "anthropic" or "offline".

        `auto` prefers whichever key is present; OpenAI wins if both are.
        An explicit choice is honoured only if its key is really there, so a
        stale setting degrades to offline instead of erroring mid-demo.
        """
        choice = (self.ai_provider or "auto").strip().lower()
        has_openai = bool(self.openai_api_key.strip())
        has_anthropic = bool(self.anthropic_api_key.strip())

        if choice == "offline":
            return "offline"
        if choice == "openai":
            return "openai" if has_openai else "offline"
        if choice == "anthropic":
            return "anthropic" if has_anthropic else "offline"

        if has_openai:
            return "openai"
        if has_anthropic:
            return "anthropic"
        return "offline"

    @property
    def ai_mode(self) -> str:
        """What the UI shows: "ai" when a model answers, else "offline"."""
        return "offline" if self.provider == "offline" else "ai"

    @property
    def model_name(self) -> str:
        return self.openai_model if self.provider == "openai" else self.ai_model


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
