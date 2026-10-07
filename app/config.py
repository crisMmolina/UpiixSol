"""Settings come only from the environment (12-factor). See `.env.example`."""

import secrets
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: Literal["dev", "test", "prod"] = "dev"
    database_url: str = "sqlite:///./upiixsol.db"
    # In dev/test a random per-process secret is fine; prod must set JWT_SECRET (checked below).
    jwt_secret: str = Field(default_factory=lambda: secrets.token_urlsafe(48))
    jwt_access_minutes: int = 15
    jwt_refresh_days: int = 7
    cookie_secure: bool = True
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]
    media_dir: str = "media"
    ratelimit_enabled: bool = True
    # Documented provisional default (IDEA §2.3); seeded users get must_change_password=true.
    seed_default_password: str = "admin123"  # noqa: S105

    @model_validator(mode="before")
    @classmethod
    def _split_origins(cls, data: dict) -> dict:
        origins = data.get("cors_origins") if isinstance(data, dict) else None
        if isinstance(origins, str):
            data["cors_origins"] = [o.strip() for o in origins.split(",") if o.strip()]
        return data

    @model_validator(mode="after")
    def _prod_requires_explicit_secret(self) -> "Settings":
        if self.env == "prod" and ("jwt_secret" not in self.model_fields_set or len(self.jwt_secret) < 32):
            raise ValueError("JWT_SECRET (>= 32 chars) is required when ENV=prod")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
