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

    # Photo evidence storage (local disk in development; swap the Storage
    # implementation in app.core.storage for object storage later).
    upload_dir: str = "uploads"
    upload_url_prefix: str = "/uploads"
    max_upload_size_bytes: int = 5 * 1024 * 1024

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


settings = Settings()
