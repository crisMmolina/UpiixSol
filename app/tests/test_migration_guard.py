"""Guard in app/migrations/env.py: no `downgrade` against a remote database (incident 2026-11-17).

Only FAKE URLs. Refused cases fail before any connection; allowed remote/localhost cases use offline
(`--sql`) mode, which renders SQL and never connects.
"""

import logging
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.util import CommandError

from app.config import get_settings

REMOTE = "postgresql+psycopg://u:p@db.example.com/x"
LOCAL = "postgresql+psycopg://u:p@localhost/x"
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def alembic_env(monkeypatch: pytest.MonkeyPatch):
    loggers = [lg for lg in logging.root.manager.loggerDict.values() if isinstance(lg, logging.Logger)]
    disabled = {lg: lg.disabled for lg in loggers}
    monkeypatch.delenv("ALEMBIC_ALLOW_REMOTE_DOWNGRADE", raising=False)

    def use(url: str) -> Config:
        monkeypatch.setenv("DATABASE_URL", url)
        get_settings.cache_clear()
        return Config(str(ROOT / "alembic.ini"))

    yield use
    get_settings.cache_clear()
    for lg, was in disabled.items():
        lg.disabled = was


def _downgrade_error(config: Config) -> Exception | None:
    try:
        command.downgrade(config, "base")
    except Exception as exc:  # noqa: BLE001 - the test inspects which error came out
        return exc
    return None


def test_downgrade_refused_on_remote_postgres(alembic_env) -> None:
    error = _downgrade_error(alembic_env(REMOTE))
    assert isinstance(error, CommandError)
    assert "ALEMBIC_ALLOW_REMOTE_DOWNGRADE" in str(error)
    assert "remota" in str(error)


def test_downgrade_allowed_on_sqlite_and_localhost(alembic_env, tmp_path: Path, capsys) -> None:
    config = alembic_env(f"sqlite:///{tmp_path / 'g.db'}")
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    for url in (LOCAL, "postgresql+psycopg://u:p@127.0.0.1/x", "postgresql+psycopg://u:p@[::1]/x"):
        command.downgrade(alembic_env(url), "0010:0009", sql=True)  # offline: no connection
    assert "DROP" in capsys.readouterr().out.upper()


def test_downgrade_allowed_on_remote_with_explicit_override(alembic_env, monkeypatch, capsys) -> None:
    config = alembic_env(REMOTE)
    monkeypatch.setenv("ALEMBIC_ALLOW_REMOTE_DOWNGRADE", "yes")
    command.downgrade(config, "0010:0009", sql=True)
    assert "DROP" in capsys.readouterr().out.upper()
    monkeypatch.setenv("ALEMBIC_ALLOW_REMOTE_DOWNGRADE", "1")  # only the exact word "yes" opens the guard
    assert isinstance(_downgrade_error(config), CommandError)


def test_upgrade_still_runs_on_remote(alembic_env, capsys) -> None:
    command.upgrade(alembic_env(REMOTE), "base:head", sql=True)
    assert "CREATE TABLE" in capsys.readouterr().out.upper()
