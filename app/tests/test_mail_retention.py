"""Mail retention (UPS-081, spec 003 §Non-functional): recipient rows go 365 days after the campaign."""

from contextlib import nullcontext
from datetime import timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.common import utcnow
from app.models.mail import MailCampaign, MailRecipient, MailSuppression
from app.services import mail_retention
from app.services.mailer import new_unsubscribe_token

SECRET_EMAIL = "persona.secreta@example.com"


def _campaign(
    db: Session, *, age_days: int | None, statuses: tuple[str, ...] = ("delivered", "failed", "delivered")
) -> MailCampaign:
    """A campaign finished `age_days` ago (None: still sending) with one recipient per status."""
    finished = None if age_days is None else utcnow() - timedelta(days=age_days)
    campaign = MailCampaign(
        audience_kind="all",
        subject="Aviso",
        body="Hola",
        status="sending" if finished is None else "sent",
        recipient_count=len(statuses),
        finished_at=finished,
    )
    db.add(campaign)
    db.flush()
    for index, status in enumerate(statuses):
        _, token_hash = new_unsubscribe_token()
        db.add(
            MailRecipient(
                campaign_id=campaign.id,
                email=f"user{campaign.id}-{index}@example.com",
                name="Ana",
                status=status,
                unsubscribe_token_hash=token_hash,
            )
        )
    db.flush()
    return campaign


def _recipient_count(db: Session, campaign_id: int) -> int:
    return (
        db.scalar(
            select(func.count()).select_from(MailRecipient).where(MailRecipient.campaign_id == campaign_id)
        )
        or 0
    )


def test_purge_deletes_recipients_of_old_campaigns_only(db: Session) -> None:
    old = _campaign(db, age_days=400)
    recent = _campaign(db, age_days=30)
    running = _campaign(db, age_days=None)

    result = mail_retention.purge(db, 365)

    assert (result.campaigns, result.recipients) == (1, 3)
    assert _recipient_count(db, old.id) == 0
    assert _recipient_count(db, recent.id) == 3
    assert _recipient_count(db, running.id) == 3
    assert db.get(MailCampaign, old.id) is not None


def test_purge_keeps_campaign_counts(db: Session) -> None:
    old = _campaign(db, age_days=400)

    mail_retention.purge(db, 365)
    db.refresh(old)

    assert old.counts_snapshot == {"delivered": 2, "failed": 1}
    assert old.recipient_count == 3
    # A second run finds nothing to delete and must not overwrite the snapshot with zeros.
    mail_retention.purge(db, 365)
    db.refresh(old)
    assert old.counts_snapshot == {"delivered": 2, "failed": 1}


def test_purge_keeps_suppressions(db: Session) -> None:
    old = _campaign(db, age_days=400)
    db.add(MailSuppression(email=SECRET_EMAIL, reason="unsubscribed", campaign_id=old.id))
    db.flush()

    mail_retention.purge(db, 365)

    assert db.get(MailSuppression, SECRET_EMAIL) is not None


def test_purge_cli_dry_run_prints_counts_only(
    db: Session, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    old = _campaign(db, age_days=400)
    db.commit()
    monkeypatch.setattr(mail_retention, "SessionLocal", lambda: nullcontext(db))

    assert mail_retention.main(["--days", "365", "--dry-run"]) == 0
    out = capsys.readouterr().out

    assert "1" in out and "3" in out
    assert "@" not in out
    assert _recipient_count(db, old.id) == 3  # dry run deletes nothing
    db.refresh(old)
    assert old.counts_snapshot is None

    assert mail_retention.main(["--days", "365"]) == 0
    capsys.readouterr()
    assert _recipient_count(db, old.id) == 0
