from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Hack API"
    debug: bool = True
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/hack"

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Built frontend (Vite `dist`) served by this app in single-container
    # deployments. Empty in local dev, where Vite serves the frontend itself.
    frontend_dist: str = ""

    upload_dir: str = "uploads"
    upload_url_prefix: str = "/uploads"
    max_upload_size_bytes: int = 5 * 1024 * 1024

    anthropic_api_key: str = ""
    photo_verification_model: str = "claude-opus-5"

    notifier: str = "console"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "SmartCity Reports <noreply@city.gov>"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("database_url", mode="before")
    @classmethod
    def normalise_database_url(cls, value):
        """Managed Postgres providers (Render, Heroku, Fly) hand out
        `postgres://` or `postgresql://` URLs. SQLAlchemy 2 resolves those to
        psycopg2, which isn't installed — name the psycopg 3 driver instead."""
        if isinstance(value, str):
            for prefix in ("postgresql://", "postgres://"):
                if value.startswith(prefix):
                    return "postgresql+psycopg://" + value[len(prefix) :]
        return value


settings = Settings()
