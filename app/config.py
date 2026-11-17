"""Settings come only from the environment (12-factor). See `.env.example`."""

import secrets
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Documented provisional default (IDEA §2.3); seeded users get must_change_password=true. Never valid in prod.
DOCUMENTED_SEED_PASSWORD = "admin123"  # noqa: S105


class Settings(BaseSettings):
    # Empty values (e.g. `JWT_SECRET=` copied from .env.example) fall back to safe defaults.
    # hide_input_in_errors: a failed validator would otherwise print every setting, API keys included.
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", env_ignore_empty=True, hide_input_in_errors=True
    )

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

    # Email channel (UPS-072, spec 003). Off unless a human turns it on; keys live only in .env or the host.
    mail_enabled: bool = False
    mail_backend: Literal["console", "mailgun"] = "console"
    mailgun_api_key: SecretStr | None = None
    mailgun_domain: str = "mg.upiixsol.com"
    mailgun_api_base: str = "https://api.mailgun.net"  # EU: https://api.eu.mailgun.net
    mailgun_webhook_signing_key: SecretStr | None = None
    mailgun_test_mode: bool = False
    mail_from: str = "UpiixSol <avisos@mg.upiixsol.com>"
    mail_reply_to: str = ""
    mail_daily_limit: int = Field(default=100, ge=0)
    mail_blocked_domains: Annotated[list[str], NoDecode] = [
        "upiixsol.dev"
    ]  # seed accounts, never deliverable
    public_base_url: str = "https://www.upiixsol.com"

    @model_validator(mode="before")
    @classmethod
    def _split_origins(cls, data: dict) -> dict:
        origins = data.get("cors_origins") if isinstance(data, dict) else None
        if isinstance(origins, str):
            data["cors_origins"] = [o.strip() for o in origins.split(",") if o.strip()]
        domains = data.get("mail_blocked_domains") if isinstance(data, dict) else None
        if isinstance(domains, str):
            data["mail_blocked_domains"] = [d.strip().lower() for d in domains.split(",") if d.strip()]
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
            if self.mail_enabled and not (
                self.mailgun_api_base.startswith("https://") and self.public_base_url.startswith("https://")
            ):
                raise ValueError(
                    "MAILGUN_API_BASE and PUBLIC_BASE_URL must be https:// when mail is enabled in prod"
                )
            if self.mail_enabled and self.mail_backend == "mailgun":
                missing = [
                    name
                    for name, given in (
                        ("MAILGUN_API_KEY", self.mailgun_api_key),
                        ("MAILGUN_DOMAIN", "mailgun_domain" in self.model_fields_set),
                        ("MAILGUN_WEBHOOK_SIGNING_KEY", self.mailgun_webhook_signing_key),
                    )
                    if not given
                ]
                if missing:
                    raise ValueError(
                        f"{', '.join(missing)} required when mail is enabled with Mailgun in prod"
                    )
        return self

    @property
    def docs_enabled(self) -> bool:
        return self.env != "prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()
