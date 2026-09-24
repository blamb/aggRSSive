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

    # Optional: Claude-powered tag suggestions. Leave the key empty and the feature simply doesn't appear.
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-4-5"

    @property
    def ai_enabled(self) -> bool:
        return bool(self.anthropic_api_key)

    # Local embeddings for "meaning" rules. Free; the model (~64 MB) downloads on first use into
    # FASTEMBED_CACHE_PATH (set to /data/models in Docker). Set EMBEDDINGS_ENABLED=false to turn off.
    embeddings_enabled: bool = True
    embedding_model: str = "BAAI/bge-small-en-v1.5"

    # LTI 1.3. The tool's RSA private key is generated on first start and kept here.
    lti_key_path: str = "./data/lti_private_key.pem"

    # Pin hostnames to IPs, e.g. "moodle.example.cloud=51.222.48.161". See netfix.py for why.
    dns_overrides: str = ""

    # Fetching
    user_agent: str = "Mozilla/5.0 (compatible; aggRSSive/2.0; +https://github.com/blamb/aggRSSive)"
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
