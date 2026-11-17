"""The backend suite is hermetic: a developer's dotenv file never changes the settings tests see (UPS-083).

`wt new` links the main checkout's dotenv file into every worktree; values copied from `.env.example`
(a real `SEED_DEFAULT_PASSWORD`, `COOKIE_SECURE=false`, `RATELIMIT_ENABLED=false`) used to fail 23 tests.
"""

import os
from pathlib import Path

import pytest

from app import db as db_module
from app.config import DOCUMENTED_SEED_PASSWORD, Settings
from app.services.media import StorageSettings

EXAMPLE = Path(__file__).resolve().parents[2] / ".env.example"
DOTENV = ".env"

# A non-default value for every key in `.env.example`, like a developer's filled-in copy.
FILLED = {
    "ENV": "dev",
    "DATABASE_URL": "sqlite:///./somewhere-else.db",
    "JWT_SECRET": "x" * 48,
    "JWT_ACCESS_MINUTES": "99",
    "JWT_REFRESH_DAYS": "99",
    "COOKIE_SECURE": "false",
    "CORS_ORIGINS": "http://localhost:9999",
    "MEDIA_DIR": "elsewhere",
    "RATELIMIT_ENABLED": "false",
    "SEED_DEFAULT_PASSWORD": "Developer-Seed-Pass-42",
    "REQUIRE_PASSWORD_CHANGE": "true",
    "MAIL_ENABLED": "true",
    "MAIL_BACKEND": "mailgun",
    "MAILGUN_API_KEY": "key-dev",
    "MAILGUN_DOMAIN": "mg.example.com",
    "MAILGUN_API_BASE": "https://api.eu.mailgun.net",
    "MAILGUN_WEBHOOK_SIGNING_KEY": "sign-dev",
    "MAILGUN_TEST_MODE": "true",
    "MAIL_FROM": "Dev <dev@example.com>",
    "MAIL_REPLY_TO": "reply@example.com",
    "MAIL_DAILY_LIMIT": "7",
    "MAIL_BLOCKED_DOMAINS": "example.com",
    "PUBLIC_BASE_URL": "https://dev.example.com",
}


def _example_keys() -> list[str]:
    lines = EXAMPLE.read_text(encoding="utf-8").splitlines()
    return [ln.split("=", 1)[0] for ln in lines if "=" in ln and not ln.lstrip().startswith("#")]


def test_settings_ignore_dotenv_under_pytest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / DOTENV).write_text(
        "SEED_DEFAULT_PASSWORD=Developer-Seed-Pass-42\nMAIL_DAILY_LIMIT=7\nMEDIA_STORAGE=database\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    for key in ("SEED_DEFAULT_PASSWORD", "MAIL_DAILY_LIMIT", "MEDIA_STORAGE"):
        monkeypatch.delenv(key, raising=False)

    assert Settings().seed_default_password == DOCUMENTED_SEED_PASSWORD
    # Every settings class of the app, not only app.config (media storage has its own, UPS-074).
    assert StorageSettings().media_storage == "disk"

    # The dotenv file may point to a remote database: under pytest neither Settings nor the global engine
    # (built when app.db was imported) may ever reach it; only an explicit DATABASE_URL (CI) is honored.
    (tmp_path / DOTENV).write_text(
        "DATABASE_URL=postgresql+psycopg://user:pass@remote.invalid:5432/upiixsol\n", encoding="utf-8"
    )
    if "DATABASE_URL" not in os.environ:
        assert Settings().database_url.startswith("sqlite")
        assert db_module.engine.url.get_backend_name() == "sqlite"
    assert "remote.invalid" not in Settings().database_url

    # Explicit environment variables (and monkeypatch) still win, as before.
    monkeypatch.setenv("MAIL_DAILY_LIMIT", "3")
    assert Settings().mail_daily_limit == 3


def test_suite_settings_match_defaults_with_a_full_dotenv_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    keys = _example_keys()
    assert set(keys) <= set(FILLED), f"fill these new .env.example keys here: {set(keys) - set(FILLED)}"
    (tmp_path / DOTENV).write_text("".join(f"{k}={FILLED[k]}\n" for k in keys), encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    settings = Settings()

    for name, field in Settings.model_fields.items():
        if name.upper() in os.environ or field.default_factory is not None:
            continue  # set by conftest/CI on purpose, or random per process (jwt_secret)
        value = getattr(settings, name)
        assert value == field.default, f"{name.upper()} leaked from the dotenv file: {value!r}"
    assert settings.jwt_secret != FILLED["JWT_SECRET"]
