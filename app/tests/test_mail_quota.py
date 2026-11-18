"""Mail quota per Mailgun billing period (UPS-092): period math, DB count, settings."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models.mail import MailCampaign, MailRecipient
from app.services import mail_audience
from app.services.mail_audience import billing_period, mail_status
from app.services.mailer import new_unsubscribe_token


def _dt(*args: int) -> datetime:
    return datetime(*args, tzinfo=UTC)


def test_period_starts_on_configured_day() -> None:
    assert billing_period(_dt(2026, 11, 17, 8), 1) == (_dt(2026, 11, 1), _dt(2026, 12, 1))
    assert billing_period(_dt(2026, 11, 17, 8), 10) == (_dt(2026, 11, 10), _dt(2026, 12, 10))
    # before the start day we are still in the period that began last month
    assert billing_period(_dt(2026, 11, 9, 23, 59), 10) == (_dt(2026, 10, 10), _dt(2026, 11, 10))
    # the start day itself, at midnight, opens the new period
    assert billing_period(_dt(2026, 11, 10), 10) == (_dt(2026, 11, 10), _dt(2026, 12, 10))


def test_period_rolls_over_at_month_end_for_short_months() -> None:
    assert billing_period(_dt(2027, 2, 20), 28) == (_dt(2027, 1, 28), _dt(2027, 2, 28))
    assert billing_period(_dt(2027, 2, 28), 28) == (_dt(2027, 2, 28), _dt(2027, 3, 28))
    assert billing_period(_dt(2026, 12, 31, 23), 28) == (_dt(2026, 12, 28), _dt(2027, 1, 28))
    assert billing_period(_dt(2027, 1, 5), 28) == (_dt(2026, 12, 28), _dt(2027, 1, 28))


def test_quota_counts_the_current_billing_period(
    db: Session, seeded: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(mail_audience, "utcnow", lambda: _dt(2026, 11, 17, 12))
    monkeypatch.setattr(get_settings(), "mail_period_start_day", 10)
    campaign = MailCampaign(
        sender_id=seeded["superadmin_id"], audience_kind="all", subject="Aviso", body="Hola", status="sent"
    )
    db.add(campaign)
    db.flush()
    rows = [
        ("accepted", _dt(2026, 11, 10)),  # first instant of the period: counts
        ("delivered", _dt(2026, 11, 16)),
        ("pending", _dt(2026, 11, 16)),  # never left pending: not counted
        ("delivered", _dt(2026, 11, 9, 23, 59)),  # previous period
    ]
    for i, (status, updated_at) in enumerate(rows):
        db.add(
            MailRecipient(
                campaign_id=campaign.id,
                email=f"q{i}@ipn.mx",
                name="Q",
                status=status,
                unsubscribe_token_hash=new_unsubscribe_token()[1],
                updated_at=updated_at,
            )
        )
    db.flush()
    status = mail_status(db)
    assert status.sent_this_period == 2
    assert status.remaining == 2998
    assert status.period_start == _dt(2026, 11, 10) and status.period_end == _dt(2026, 12, 10)


def test_monthly_settings_defaults_and_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("MAIL_MONTHLY_LIMIT", "MAIL_PERIOD_START_DAY", "MAIL_DAILY_LIMIT"):
        monkeypatch.delenv(name, raising=False)
    settings = Settings(_env_file=None)
    assert settings.mail_monthly_limit == 3000 and settings.mail_period_start_day == 1
    assert not hasattr(settings, "mail_daily_limit")
    monkeypatch.setenv("MAIL_DAILY_LIMIT", "100")  # an old value is ignored, never a crash
    assert Settings(_env_file=None).mail_monthly_limit == 3000
    bad_values = (("MAIL_PERIOD_START_DAY", "0"), ("MAIL_PERIOD_START_DAY", "29"))
    for name, bad in (*bad_values, ("MAIL_MONTHLY_LIMIT", "-1")):
        monkeypatch.setenv(name, bad)
        with pytest.raises(ValidationError):
            Settings(_env_file=None)
        monkeypatch.delenv(name)
