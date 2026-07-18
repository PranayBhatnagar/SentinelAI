from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration is injected, never read directly by domain code."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="SENTINEL_", extra="ignore")

    environment: str = "development"
    database_url: str = "sqlite+aiosqlite:///./sentinel.db"
    redis_url: str = "redis://localhost:6379/0"
    github_webhook_secret: str = ""
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    agent_timeout_seconds: float = 20.0
    github_token: str | None = None
    github_api_url: str = "https://api.github.com"
    prometheus_url: str | None = None
    loki_url: str | None = None
    grafana_url: str | None = None
    grafana_token: str | None = None
    argocd_url: str | None = None
    argocd_token: str | None = None
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    jwt_secret: str = ""
    connector_cache_ttl_seconds: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
