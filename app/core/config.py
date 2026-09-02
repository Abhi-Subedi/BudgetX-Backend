from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    project_name: str = "BudgetX API"
    environment: str = "development"

    database_url: str = Field(validation_alias="DATABASE_URL")

    secret_key: str = Field(validation_alias="SECRET_KEY")

    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14

    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://budget-x-ch9q.vercel.app",
        "https://budget-x-drab.vercel.app",
        "https://budgetx.abhinandansubedi.com.np/
    ]

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""

    # Apple Sign In
    apple_client_id: str = ""
    apple_team_id: str = ""
    apple_key_id: str = ""
    apple_private_key: str = ""

    frontend_url: str = "http://localhost:3000"

    frontend_url_production: str = "https://budget-x-ch9q.vercel.app"

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError(
                "SECRET_KEY must be at least 32 characters long"
            )
        return v

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        if v not in ("development", "staging", "production"):
            raise ValueError(
                "ENVIRONMENT must be development, staging, or production"
            )
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()