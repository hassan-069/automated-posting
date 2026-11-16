"""Application settings, loaded from environment variables / .env file."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Networking
    request_timeout: float = 15.0   # per HTTP request
    platform_timeout: float = 30.0  # per platform, end to end

    # Dev.to
    devto_api_key: str | None = None


    # Mastodon
    mastodon_base_url: str = "https://mastodon.social"
    mastodon_access_token: str | None = None

    # Bluesky
    bluesky_handle: str | None = None
    bluesky_app_password: str | None = None
    bluesky_pds_url: str = "https://bsky.social"


    # Hugging Face (LLM Platform)
    hf_token: str | None = None
    hf_repo_id: str | None = None

    # GitHub Gist
    github_token: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
