"""Calendar for the email event card (UPS-087, spec 004): RFC 5545 `.ics`, Google and Outlook links.

    event = resolve_event(db, sender, block)        # campus event (club scope from the DB row) or typed
    ics = build_ics(event, ics_uid(token))          # bytes, CRLF, folded at 75 octets, UTC times
    google_url(event) · outlook_url(event)          # template / deeplink URLs

The `.ics` is `METHOD:PUBLISH` and carries no attendee data. The UID comes from the campaign's random
`ics_token`, so a re-download is the same event for the calendar app (it updates instead of duplicating).
"""

import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import quote, urlencode

from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import Event, User
from app.security import ensure_academy_scope
from app.services.mail_blocks import EventBlock

PRODID = "-//UpiixSol//Campus//ES"
UID_DOMAIN = "upiixsol.com"
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


@dataclass(frozen=True)
class CalendarEvent:
    title: str
    start: datetime  # aware, any zone; written in UTC
    end: datetime
    place: str | None = None
    description: str | None = None
    link: str | None = None


def new_ics_token() -> str:
    """43 URL-safe characters (32 random bytes): fits `mail_campaigns.ics_token`."""
    return secrets.token_urlsafe(32)


def ics_uid(token: str) -> str:
    return f"{token}@{UID_DOMAIN}"


def _escape(value: str) -> str:
    value = _CONTROL.sub("", value).replace("\r\n", "\n").replace("\r", "\n")
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fold(line: str) -> str:
    """Lines longer than 75 octets continue on the next line after one space; never split a character."""
    out: list[str] = []
    current = ""
    size = 0
    limit = 75
    for char in line:
        width = len(char.encode("utf-8"))
        if size + width > limit:
            out.append(current)
            current, size, limit = " ", 1, 75  # the leading space counts toward the 75
        current += char
        size += width
    out.append(current)
    return "\r\n".join(out)


def _utc(value: datetime) -> datetime:
    return (value.replace(tzinfo=UTC) if value.tzinfo is None else value).astimezone(UTC)


def _stamp(value: datetime) -> str:
    return _utc(value).strftime("%Y%m%dT%H%M%SZ")


def build_ics(event: CalendarEvent, uid: str, *, stamp: datetime | None = None) -> bytes:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PRODID}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{_escape(uid)}",
        f"DTSTAMP:{_stamp(stamp or datetime.now(UTC))}",
        f"DTSTART:{_stamp(event.start)}",
        f"DTEND:{_stamp(event.end)}",
        f"SUMMARY:{_escape(event.title)}",
    ]
    if event.place:
        lines.append(f"LOCATION:{_escape(event.place)}")
    if event.description:
        lines.append(f"DESCRIPTION:{_escape(event.description)}")
    if event.link:
        lines.append(f"URL:{_CONTROL.sub('', event.link).strip()}")  # a URI value: no TEXT escaping
    lines += ["END:VEVENT", "END:VCALENDAR"]
    return "".join(_fold(line) + "\r\n" for line in lines).encode("utf-8")


def _details(event: CalendarEvent) -> str:
    return "\n\n".join(part for part in (event.description, event.link) if part)


def google_url(event: CalendarEvent) -> str:
    params = {
        "action": "TEMPLATE",
        "text": event.title,
        "dates": f"{_stamp(event.start)}/{_stamp(event.end)}",
    }
    if event.place:
        params["location"] = event.place
    if details := _details(event):
        params["details"] = details
    return "https://calendar.google.com/calendar/render?" + urlencode(params, quote_via=quote, safe="/")


def outlook_url(event: CalendarEvent) -> str:
    params = {
        "subject": event.title,
        "startdt": _utc(event.start).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "enddt": _utc(event.end).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if event.place:
        params["location"] = event.place
    if details := _details(event):
        params["body"] = details
    return "https://outlook.live.com/calendar/0/deeplink/compose?" + urlencode(params)


def resolve_event(db: Session, sender: User, block: EventBlock) -> CalendarEvent:
    """The event of an `event` block. A campus event is read from the DB; the club scope comes from its
    row (global events are open to every sender, a club's events only to its admin and superadmins)."""
    if block.event_id is None:
        assert block.title and block.start and block.end  # the block validator guarantees it  # noqa: S101
        return CalendarEvent(block.title, block.start, block.end, block.place, block.description, block.link)
    row = db.get(Event, block.event_id)
    if row is None:
        raise AppError(404, "El evento no existe.")
    if row.academy_id is not None:
        ensure_academy_scope(sender, row.academy_id)
    return CalendarEvent(
        row.title, row.starts_at, row.ends_at, row.location, row.description or None, row.link
    )
