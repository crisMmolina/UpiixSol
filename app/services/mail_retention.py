"""Mail retention (UPS-081, spec 003 §Non-functional): recipient rows go N days after the campaign finished.

Before a campaign's rows are deleted, its counts per status are stored in `counts_snapshot`, so the history
keeps its numbers. Suppressions are never touched (they must outlive the campaigns). Output is counts only.

Run monthly: `python -m app.services.mail_retention [--days 365] [--dry-run]` (docs/mail-mailgun.md).
"""

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.common import utcnow
from app.models.mail import MailCampaign, MailRecipient

DEFAULT_DAYS = 365


@dataclass(frozen=True)
class PurgeResult:
    campaigns: int  # campaigns that had recipient rows to delete
    recipients: int  # recipient rows deleted (or that would be, in a dry run)


def purge(
    db: Session, days: int = DEFAULT_DAYS, *, dry_run: bool = False, now: datetime | None = None
) -> PurgeResult:
    """Delete the recipients of campaigns finished more than `days` days ago; commits unless `dry_run`."""
    cutoff = (now or utcnow()) - timedelta(days=days)
    campaigns = db.scalars(
        select(MailCampaign).where(MailCampaign.finished_at.is_not(None), MailCampaign.finished_at < cutoff)
    ).all()
    touched = 0
    deleted = 0
    for campaign in campaigns:
        counts = dict(
            db.execute(
                select(MailRecipient.status, func.count())
                .where(MailRecipient.campaign_id == campaign.id)
                .group_by(MailRecipient.status)
            ).all()
        )
        if not counts:
            continue  # already purged: keep the stored snapshot
        touched += 1
        deleted += sum(counts.values())
        if dry_run:
            continue
        campaign.counts_snapshot = counts
        db.execute(delete(MailRecipient).where(MailRecipient.campaign_id == campaign.id))
    if dry_run:
        db.rollback()
    else:
        db.commit()
    return PurgeResult(campaigns=touched, recipients=deleted)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Delete mail recipient rows of old campaigns (counts only output)."
    )
    parser.add_argument(
        "--days", type=int, default=DEFAULT_DAYS, help="age after the campaign finished (default 365)"
    )
    parser.add_argument("--dry-run", action="store_true", help="print the counts without deleting")
    args = parser.parse_args(argv)
    if args.days < 1:
        parser.error("--days must be at least 1")
    with SessionLocal() as db:
        result = purge(db, args.days, dry_run=args.dry_run)
    verb = "would delete" if args.dry_run else "deleted"
    print(f"{verb} {result.recipients} recipient rows from {result.campaigns} campaigns (> {args.days} days)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
