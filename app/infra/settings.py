from functools import lru_cache
import json
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        enable_decoding=False,
        extra="ignore",
        populate_by_name=True,
    )

    app_env: Literal["development", "staging", "production"] = Field(
        default="development",
        alias="APP_ENV",
    )
    database_url: str = Field(
        default="postgresql+psycopg2://chat_user:chat_password@localhost:5432/chat_app",
        alias="DATABASE_URL",
    )
    jwt_secret_key: SecretStr = Field(
        default=SecretStr("change-me-in-development"),
        alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=60, ge=1, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    message_rate_limit_max_events: int = Field(default=20, ge=1, alias="MESSAGE_RATE_LIMIT_MAX_EVENTS")
    message_rate_limit_window_seconds: int = Field(default=60, ge=1, alias="MESSAGE_RATE_LIMIT_WINDOW_SECONDS")
    auth_rate_limit_max_events: int = Field(default=10, ge=1, alias="AUTH_RATE_LIMIT_MAX_EVENTS")
    auth_rate_limit_window_seconds: int = Field(default=60, ge=1, alias="AUTH_RATE_LIMIT_WINDOW_SECONDS")
    rate_limit_storage_uri: str = Field(default="memory://", alias="RATE_LIMIT_STORAGE_URI")
    rate_limit_strategy: Literal["fixed-window", "moving-window", "sliding-window-counter"] = Field(
        default="moving-window",
        alias="RATE_LIMIT_STRATEGY",
    )
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        alias="CORS_ORIGINS",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            stripped_value = value.strip()
            if stripped_value.startswith("["):
                return json.loads(stripped_value)
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def validate_production_secrets(self) -> Self:
        if self.app_env == "production" and self.jwt_secret_key.get_secret_value() == "change-me-in-development":
            raise ValueError("JWT_SECRET_KEY must be set in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
