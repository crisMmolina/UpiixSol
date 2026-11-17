"""Email channel contract (UPS-072): tables, migration 0009, settings and the transport interface.

Spec: docs/specs/003-correo/plan.md §Data and migrations, §Contracts. UPS-073..077 build on it.
"""

import hashlib
import logging
import sys
import types
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import MailCampaign, MailRecipient, MailSuppression
from app.services import mailer

MAIL_TABLES = {"mail_campaigns", "mail_recipients", "mail_suppressions"}
MAIL_ENV = (
    "ENV",
    "JWT_SECRET",
    "SEED_DEFAULT_PASSWORD",
    "MAIL_ENABLED",
    "MAIL_BACKEND",
    "MAILGUN_API_KEY",
    "MAILGUN_DOMAIN",
    "MAILGUN_API_BASE",
    "MAILGUN_WEBHOOK_SIGNING_KEY",
    "MAILGUN_TEST_MODE",
    "MAIL_FROM",
    "MAIL_REPLY_TO",
    "MAIL_DAILY_LIMIT",
    "MAIL_BLOCKED_DOMAINS",
    "PUBLIC_BASE_URL",
)
API_KEY = "key-0123456789abcdef0123456789abcdef"
SIGNING_KEY = "signing-0123456789abcdef"


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for name in MAIL_ENV:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def _prod_mailgun_env(monkeypatch: pytest.MonkeyPatch, **overrides: str) -> None:
    values = {
        "ENV": "prod",
        "JWT_SECRET": "x" * 40,
        "SEED_DEFAULT_PASSWORD": "a-long-seed-password",
        "MAIL_ENABLED": "true",
        "MAIL_BACKEND": "mailgun",
        "MAILGUN_API_KEY": API_KEY,
        "MAILGUN_DOMAIN": "mg.upiixsol.com",
        "MAILGUN_WEBHOOK_SIGNING_KEY": SIGNING_KEY,
    }
    values.update(overrides)
    for name, value in values.items():
        monkeypatch.setenv(name, value)


def _campaign(db: Session) -> MailCampaign:
    campaign = MailCampaign(
        audience_kind="all",
        audience_params={},
        subject="Hola",
        body="Cuerpo",
        status="draft",
        recipient_count=0,
    )
    db.add(campaign)
    db.flush()
    return campaign


def _recipient(campaign_id: int, email: str, token_hash: str) -> MailRecipient:
    return MailRecipient(
        campaign_id=campaign_id, email=email, name="Ana", status="pending", unsubscribe_token_hash=token_hash
    )


def test_mail_migration_round_trips(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from alembic import command
    from alembic.config import Config

    from app.config import get_settings

    url = f"sqlite:///{tmp_path / 'mail.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    engine = create_engine(url)
    # env.py runs logging.fileConfig, which disables loggers created so far: restore them for later tests.
    loggers = [
        logger for logger in logging.root.manager.loggerDict.values() if isinstance(logger, logging.Logger)
    ]
    disabled = {logger: logger.disabled for logger in loggers}
    try:
        config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
        command.upgrade(config, "head")
        inspector = inspect(engine)
        assert set(inspector.get_table_names()) >= MAIL_TABLES
        recipients = {index["name"] for index in inspector.get_indexes("mail_recipients")}
        assert {"ix_mail_recipients_status", "ix_mail_recipients_created_at"} <= recipients
        command.downgrade(config, "0008")
        assert not MAIL_TABLES & set(inspect(engine).get_table_names())
        assert "users" in inspect(engine).get_table_names()  # additive only: nothing existing was touched
        command.downgrade(config, "base")
        command.upgrade(config, "head")
    finally:
        engine.dispose()
        get_settings.cache_clear()
        for logger, was_disabled in disabled.items():
            logger.disabled = was_disabled


def test_recipient_email_is_unique_per_campaign(db: Session) -> None:
    first, second = _campaign(db), _campaign(db)
    db.add(_recipient(first.id, "ana@ipn.mx", "a" * 64))
    db.add(_recipient(second.id, "ana@ipn.mx", "b" * 64))  # the same address in another campaign is fine
    db.flush()
    db.add(_recipient(first.id, "ana@ipn.mx", "c" * 64))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_suppression_is_keyed_by_normalized_email(db: Session) -> None:
    db.add(MailSuppression(email=mailer.normalize_email("  Ana@IPN.mx "), reason="unsubscribed"))
    db.flush()
    assert db.scalar(select(MailSuppression.email)) == "ana@ipn.mx"
    db.add(MailSuppression(email=mailer.normalize_email("ANA@ipn.MX"), reason="bounced"))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_unsubscribe_token_hash_is_unique(db: Session) -> None:
    campaign = _campaign(db)
    db.add(_recipient(campaign.id, "ana@ipn.mx", "d" * 64))
    db.add(_recipient(campaign.id, "luis@ipn.mx", "d" * 64))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


@pytest.mark.parametrize(
    ("column", "value"),
    [("status", "queued"), ("audience_kind", "everyone")],
)
def test_campaign_statuses_and_audience_kinds_are_checked(db: Session, column: str, value: str) -> None:
    campaign = MailCampaign(
        audience_kind="all",
        audience_params={},
        subject="Hola",
        body="Cuerpo",
        status="draft",
        recipient_count=0,
    )
    setattr(campaign, column, value)
    db.add(campaign)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_recipient_and_suppression_values_are_checked(db: Session) -> None:
    campaign = _campaign(db)
    bad = _recipient(campaign.id, "ana@ipn.mx", "e" * 64)
    bad.status = "read"
    db.add(bad)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()
    db.add(MailSuppression(email="x@ipn.mx", reason="because"))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_mail_disabled_by_default(clean_env: pytest.MonkeyPatch) -> None:
    settings = Settings(_env_file=None)
    assert settings.mail_enabled is False
    assert settings.mail_backend == "console"
    assert settings.mailgun_api_key is None and settings.mailgun_webhook_signing_key is None
    assert settings.mailgun_domain == "mg.upiixsol.com"
    assert settings.mailgun_api_base == "https://api.mailgun.net"
    assert settings.mailgun_test_mode is False
    assert settings.mail_from == "UpiixSol <avisos@mg.upiixsol.com>"
    assert settings.mail_reply_to == ""
    assert settings.mail_daily_limit == 100
    assert settings.mail_blocked_domains == ["upiixsol.dev"]
    assert settings.public_base_url == "https://www.upiixsol.com"


def test_mail_settings_read_the_environment(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("MAIL_BLOCKED_DOMAINS", "upiixsol.dev, Example.COM ,")
    clean_env.setenv("MAILGUN_API_KEY", API_KEY)
    clean_env.setenv("MAILGUN_API_BASE", "https://api.eu.mailgun.net")
    settings = Settings(_env_file=None)
    assert settings.mail_blocked_domains == ["upiixsol.dev", "example.com"]
    assert settings.mailgun_api_key is not None and settings.mailgun_api_key.get_secret_value() == API_KEY
    assert settings.mailgun_api_base == "https://api.eu.mailgun.net"


@pytest.mark.parametrize("missing", ["MAILGUN_API_KEY", "MAILGUN_DOMAIN", "MAILGUN_WEBHOOK_SIGNING_KEY"])
def test_prod_requires_mailgun_settings_when_mail_enabled(
    clean_env: pytest.MonkeyPatch, missing: str
) -> None:
    _prod_mailgun_env(clean_env)
    clean_env.delenv(missing)  # an empty or unset value is "not set", even for the one with a default
    with pytest.raises(ValidationError, match=missing) as raised:
        Settings(_env_file=None)
    assert API_KEY not in str(raised.value) and SIGNING_KEY not in str(raised.value)


def test_prod_mail_settings_ok_when_complete_or_not_needed(clean_env: pytest.MonkeyPatch) -> None:
    _prod_mailgun_env(clean_env)
    settings = Settings(_env_file=None)
    assert settings.mail_enabled and settings.mail_backend == "mailgun"
    assert API_KEY not in repr(settings) and SIGNING_KEY not in repr(settings)
    for name, value in (("MAIL_ENABLED", "false"), ("MAIL_BACKEND", "console")):
        _prod_mailgun_env(clean_env)
        clean_env.delenv("MAILGUN_API_KEY")
        clean_env.setenv(name, value)
        Settings(_env_file=None)  # kill switch off, or console backend: no Mailgun keys needed


def test_secrets_never_appear_in_validation_errors(clean_env: pytest.MonkeyPatch) -> None:
    _prod_mailgun_env(clean_env, MAIL_DAILY_LIMIT="many")  # an unrelated bad value next to real keys
    with pytest.raises(ValidationError) as raised:
        Settings(_env_file=None)
    assert API_KEY not in str(raised.value) and SIGNING_KEY not in str(raised.value)


def test_console_transport_logs_count_without_addresses(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(mailer.logger, "disabled", False)  # an earlier alembic run may have disabled it
    message = mailer.MailMessage(subject="Secreto del club", html="<p>Hola</p>", text="Hola", campaign_id=7)
    recipients = [
        mailer.MailRecipientVars(
            recipient_id=1, email="ana@ipn.mx", name="Ana", unsubscribe_url="https://x.test/baja?t=abc"
        ),
        mailer.MailRecipientVars(
            recipient_id=2, email="luis@ipn.mx", name="Luis", unsubscribe_url="https://x.test/baja?t=def"
        ),
    ]
    with caplog.at_level(logging.INFO, logger=mailer.logger.name):
        result = mailer.ConsoleTransport().send_batch(message, recipients)
    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert "recipients=2" in logged and f"subject_length={len(message.subject)}" in logged
    for private in ("ana@ipn.mx", "luis@ipn.mx", "Secreto", "Ana", "abc"):
        assert private not in logged
    assert set(result.accepted) == {1, 2} and result.failed == {}
    assert all(provider_id.startswith("console-") for provider_id in result.accepted.values())


def test_get_mail_transport_follows_the_backend(clean_env: pytest.MonkeyPatch) -> None:
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        assert isinstance(mailer.get_mail_transport(), mailer.ConsoleTransport)
        clean_env.setenv("MAIL_BACKEND", "mailgun")
        get_settings.cache_clear()
        clean_env.setitem(sys.modules, "app.services.mailgun", None)  # import → ModuleNotFoundError
        with pytest.raises(RuntimeError, match="UPS-073"):  # the module is missing
            mailer.get_mail_transport()
        fake = types.ModuleType("app.services.mailgun")
        fake.MailgunTransport = type("MailgunTransport", (), {})  # type: ignore[attr-defined]
        clean_env.setitem(sys.modules, "app.services.mailgun", fake)
        assert isinstance(mailer.get_mail_transport(), fake.MailgunTransport)  # type: ignore[attr-defined]
    finally:
        get_settings.cache_clear()


def test_unsubscribe_token_is_random_and_only_its_hash_is_stored() -> None:
    pairs = [mailer.new_unsubscribe_token() for _ in range(50)]
    tokens = [token for token, _ in pairs]
    assert len(set(tokens)) == 50  # random, never derived from the user or the address
    for token, token_hash in pairs:
        assert len(token) >= 43  # token_urlsafe(32): 32 bytes of randomness
        assert token_hash == hashlib.sha256(token.encode()).hexdigest() and len(token_hash) == 64
        assert token not in token_hash
    columns = set(MailRecipient.__table__.columns.keys())
    assert "unsubscribe_token_hash" in columns
    assert not {"unsubscribe_token", "token"} & columns  # the plain token has no column to live in


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Ana@IPN.mx", "ana@ipn.mx"),
        ("  luis@ipn.mx\t", "luis@ipn.mx"),
        ("MAYUS@EXAMPLE.COM\n", "mayus@example.com"),
    ],
)
def test_normalize_email_lowercases_and_trims(raw: str, expected: str) -> None:
    assert mailer.normalize_email(raw) == expected


def test_stored_emails_must_be_lowercase(db: Session) -> None:
    campaign = _campaign(db)
    db.add(MailSuppression(email="Ana@ipn.mx", reason="unsubscribed"))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()
    campaign = _campaign(db)
    db.add(_recipient(campaign.id, "Ana@ipn.mx", "f" * 64))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_transport_value_objects_do_not_repr_addresses_or_tokens() -> None:
    message = mailer.MailMessage(subject="Secreto", html="<p>x</p>", text="x")
    person = mailer.MailRecipientVars(1, "ana@ipn.mx", "Ana", "https://x.test/baja?t=tok")
    shown = repr(message) + repr(person)
    for private in ("Secreto", "ana@ipn.mx", "Ana", "tok"):
        assert private not in shown


def test_prod_mail_needs_https_urls(clean_env: pytest.MonkeyPatch) -> None:
    _prod_mailgun_env(clean_env, MAILGUN_API_BASE="http://api.mailgun.net")
    with pytest.raises(ValidationError, match="https"):
        Settings(_env_file=None)
    _prod_mailgun_env(clean_env, PUBLIC_BASE_URL="http://www.upiixsol.com")
    with pytest.raises(ValidationError, match="https"):
        Settings(_env_file=None)
