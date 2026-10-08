"""Settings come only from the environment (12-factor). See `.env.example`."""

import secrets
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Documented provisional default (IDEA §2.3); seeded users get must_change_password=true. Never valid in prod.
DOCUMENTED_SEED_PASSWORD = "admin123"  # noqa: S105


class Settings(BaseSettings):
    # Empty values (e.g. `JWT_SECRET=` copied from .env.example) fall back to safe defaults.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)

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
    seed_default_password: str = DOCUMENTED_SEED_PASSWORD
    # Accounts with must_change_password can only change it until they do (UPS-020). `false` only for a demo
    # with the seeded accounts (IDEA §2.3).
    require_password_change: bool = True

    @model_validator(mode="before")
    @classmethod
    def _split_origins(cls, data: dict) -> dict:
        origins = data.get("cors_origins") if isinstance(data, dict) else None
        if isinstance(origins, str):
            data["cors_origins"] = [o.strip() for o in origins.split(",") if o.strip()]
        return data

    @model_validator(mode="after")
    def _safe_values(self) -> "Settings":
        if len(self.jwt_secret) < 32:
            raise ValueError("JWT_SECRET must have >= 32 chars")
        if "*" in self.cors_origins:
            raise ValueError("CORS_ORIGINS cannot be '*' (credentials are allowed)")
        if self.env == "prod":
            if "jwt_secret" not in self.model_fields_set:
                raise ValueError("JWT_SECRET is required when ENV=prod")
            seed = self.seed_default_password
            weak_seed = len(seed) < 12 or seed == DOCUMENTED_SEED_PASSWORD
            if "seed_default_password" not in self.model_fields_set or weak_seed:
                raise ValueError("SEED_DEFAULT_PASSWORD (>= 12 chars, not the default) is required in prod")
        return self

    @property
    def docs_enabled(self) -> bool:
        return self.env != "prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()
