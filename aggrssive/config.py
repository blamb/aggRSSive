from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    secret_key: str = "dev-only-insecure-key"
    base_url: str = "http://localhost:8000"
    database_url: str = "sqlite:///./data/aggrssive.db"
    poll_interval_minutes: int = 30
    allow_signup: bool = True

    github_client_id: str = ""
    github_client_secret: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""

    # Fetching
    user_agent: str = "aggRSSive/2.0 (+https://github.com/brianlamb/aggrssive)"
    fetch_timeout_seconds: float = 20.0
    max_items_per_source: int = 500  # keep the newest N per source

    @property
    def github_enabled(self) -> bool:
        return bool(self.github_client_id and self.github_client_secret)

    @property
    def google_enabled(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)


@lru_cache
def get_settings() -> Settings:
    return Settings()
