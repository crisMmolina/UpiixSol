"""Opt-out of club email (UPS-076, spec 003 §Opt-out): the one-click unsubscribe and the account preference.

    unsubscribe_by_token(db, token)        # public: the token (sent in the email) is the only credential
    get_preference(db, user)               # "Recibir correos del club" for the user's current address
    set_preference(db, user, receive)      # False adds the suppression; True lifts only an `unsubscribed` one

Suppressions are keyed by the normalized address (`mailer.normalize_email`), so they cover campus users and
outside addresses alike. A bounce or a complaint is never lifted from here: it is not the person's choice.
"""

import hashlib

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import User
from app.models.mail import MailRecipient, MailSuppression
from app.services.mailer import normalize_email


class PreferencesIn(BaseModel):
    receive_club_email: bool


class PreferencesOut(BaseModel):
    receive_club_email: bool


def add_suppression(db: Session, email: str, reason: str, campaign_id: int | None) -> None:
    if db.get(MailSuppression, email) is not None:
        return  # already suppressed (maybe for a stronger reason): keep that row
    try:
        with db.begin_nested():
            db.add(MailSuppression(email=email, reason=reason, campaign_id=campaign_id))
    except IntegrityError:
        pass  # a concurrent request added it first


def unsubscribe_by_token(db: Session, token: str | None) -> None:
    """Suppress the address of the recipient that owns `token`. Unknown or missing tokens do nothing, and
    the caller answers the same either way (no oracle on which tokens or addresses exist)."""
    if not token:
        return
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    recipient = db.execute(
        select(MailRecipient.email, MailRecipient.campaign_id).where(
            MailRecipient.unsubscribe_token_hash == token_hash
        )
    ).first()
    if recipient is not None:
        add_suppression(db, normalize_email(recipient.email), "unsubscribed", recipient.campaign_id)


def get_preference(db: Session, user: User) -> PreferencesOut:
    return PreferencesOut(receive_club_email=db.get(MailSuppression, normalize_email(user.email)) is None)


def set_preference(db: Session, user: User, receive: bool) -> PreferencesOut:
    email = normalize_email(user.email)
    if receive:
        row = db.get(MailSuppression, email)
        if row is not None and row.reason == "unsubscribed":
            db.delete(row)
    else:
        add_suppression(db, email, "unsubscribed", None)
    db.flush()
    return get_preference(db, user)
