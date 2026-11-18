"""Alembic environment: URL from app.config, metadata from app.db.Base (models in app/models/)."""

import contextlib
import importlib
import os
from logging.config import fileConfig

from alembic import context
from alembic.util import CommandError
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import make_url

from app.config import get_settings
from app.db import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
config.set_main_option("sqlalchemy.url", get_settings().database_url)

# Register every model on Base.metadata. app/models/ is created by UPS-002.
with contextlib.suppress(ModuleNotFoundError):
    importlib.import_module("app.models")

target_metadata = Base.metadata


LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _refuse_remote_downgrade() -> None:
    """Incident 2026-11-17: a `downgrade base` reached the production DB through the linked dotenv file.

    Runs before any connection is opened. Upgrades are never affected.
    """
    url = make_url(config.get_main_option("sqlalchemy.url", ""))
    if url.get_backend_name() == "sqlite" or (url.host or "") in LOCAL_HOSTS:
        return
    if os.environ.get("ALEMBIC_ALLOW_REMOTE_DOWNGRADE") == "yes":
        return
    # Only to read which command is running (opens no connection); env.py configures again below.
    context.configure(url=url.render_as_string(hide_password=False))
    fn = context.get_context().opts.get("fn")
    if getattr(fn, "__name__", None) != "downgrade":
        return
    raise CommandError(
        f"Downgrade rechazado: la base de datos es remota (host «{url.host}»). Un downgrade borra tablas y "
        "datos. Apunta DATABASE_URL a SQLite o a localhost (p. ej. DATABASE_URL=sqlite:////tmp/rt.db). "
        "Si de verdad es lo que quieres, repite ese único comando con ALEMBIC_ALLOW_REMOTE_DOWNGRADE=yes."
    )


def _is_sqlite() -> bool:
    return config.get_main_option("sqlalchemy.url", "").startswith("sqlite")


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=_is_sqlite(),
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=_is_sqlite(),
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


_refuse_remote_downgrade()
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
