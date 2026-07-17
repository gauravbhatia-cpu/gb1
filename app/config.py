"""
Central configuration. Everything is optional except DATABASE_URL --
connectors check their own required keys at call time and skip themselves
with a clear log message if a key is missing, rather than crashing the
whole pipeline because one platform isn't configured yet.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", ".env.local"), extra="ignore")

    database_url: str = "sqlite:///./data/social_intel.db"
    postgres_url: str | None = None

    supabase_url: str | None = None
    supabase_publishable_key: str | None = None
    supabase_anon_key: str | None = None

    x_bearer_token: str | None = None

    meta_access_token: str | None = None
    meta_ad_library_country: str = "US"

    news_api_key: str | None = None

    anthropic_api_key: str | None = None

    poll_interval_minutes: int = 60


settings = Settings()
