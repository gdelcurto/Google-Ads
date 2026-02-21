"""Application configuration via environment variables."""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_env: str = "development"
    app_secret_key: str = "dev-secret-key"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # DB
    database_url: str = "sqlite+aiosqlite:///./data/google_ads_campaigns.db"

    # JWT
    jwt_secret_key: str = "dev-jwt-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 480

    # Google Ads API
    google_ads_developer_token: str = ""
    google_ads_client_id: str = ""
    google_ads_client_secret: str = ""
    google_ads_refresh_token: str = ""
    google_ads_login_customer_id: str = ""

    # Translation
    translation_provider: str = "noop"
    google_translate_api_key: str = ""
    deepl_api_key: str = ""

    # Anthropic (for AI auto-fill brief from hotel website)
    anthropic_api_key: str = ""

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Default admin
    admin_email: str = "admin@blastness.com"
    admin_password: str = "admin123"
    admin_full_name: str = "Admin"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def is_google_ads_configured(self) -> bool:
        return bool(
            self.google_ads_developer_token
            and self.google_ads_client_id
            and self.google_ads_refresh_token
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
