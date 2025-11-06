"""
Application configuration using Pydantic Settings.
Loads configuration from environment variables and .env file.
"""
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    app_name: str = Field(default="E-Commerce Intelligence SaaS")
    app_version: str = Field(default="1.0.0")
    debug: bool = Field(default=False)
    secret_key: str = Field(default="change-me-in-production")
    api_v1_prefix: str = Field(default="/api/v1")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/ecommerce_saas"
    )
    database_pool_size: int = Field(default=20)
    database_max_overflow: int = Field(default=10)

    # CORS
    allowed_origins: str = Field(default="http://localhost:3000,http://localhost:8000")
    allowed_methods: str = Field(default="*")
    allowed_headers: str = Field(default="*")

    @field_validator("allowed_origins")
    @classmethod
    def parse_cors_origins(cls, v: str) -> List[str]:
        """Parse comma-separated CORS origins into a list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # JWT
    jwt_secret_key: str = Field(default="change-me-in-production")
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)
    refresh_token_expire_days: int = Field(default=7)

    # Stripe
    stripe_api_key: str = Field(default="")
    stripe_webhook_secret: str = Field(default="")
    stripe_price_id_free: str = Field(default="price_free")
    stripe_price_id_starter: str = Field(default="price_starter")
    stripe_price_id_pro: str = Field(default="price_pro")
    stripe_price_id_agency: str = Field(default="price_agency")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")
    redis_password: Optional[str] = Field(default=None)

    # Celery
    celery_broker_url: str = Field(default="redis://localhost:6379/1")
    celery_result_backend: str = Field(default="redis://localhost:6379/2")

    # Scraping
    scraping_user_agent: str = Field(
        default="Mozilla/5.0 (compatible; EcommerceSaaS/1.0)"
    )
    scraping_timeout: int = Field(default=30)
    scraping_max_retries: int = Field(default=3)
    scraping_rate_limit: int = Field(default=10)

    # Email
    smtp_host: str = Field(default="smtp.gmail.com")
    smtp_port: int = Field(default=587)
    smtp_user: Optional[str] = Field(default=None)
    smtp_password: Optional[str] = Field(default=None)
    email_from: str = Field(default="noreply@example.com")

    # Monitoring
    sentry_dsn: Optional[str] = Field(default=None)
    log_level: str = Field(default="INFO")

    # Subscription Limits
    free_tier_searches: int = Field(default=10)
    starter_tier_searches: int = Field(default=100)
    pro_tier_searches: int = Field(default=1000)
    agency_tier_searches: int = Field(default=10000)

    def get_search_limit(self, tier: str) -> int:
        """Get search limit for a given subscription tier."""
        limits = {
            "free": self.free_tier_searches,
            "starter": self.starter_tier_searches,
            "pro": self.pro_tier_searches,
            "agency": self.agency_tier_searches,
        }
        return limits.get(tier.lower(), self.free_tier_searches)


# Global settings instance
settings = Settings()
