"""Usage analytics (UPS-037): what students do and use, appended to `activity_events`.

Two sources feed the same table (catalogue and dashboard queries in docs/analytics.md):

- server: `capture()` runs in the request middleware (app/main.py). After a 2xx response it maps the matched
  route template + method to an event (SERVER_EVENTS) and writes it in a background task with its own short
  session, so other routers and services need no changes and a failing write never touches the response.
- web: `POST /api/analytics/events` (app/routers/analytics.py) takes small batches from the web tracker
  (web/src/lib/analytics.ts: page views, video play/pause/end, searches, resource opens) for signed-in users.

`ANALYTICS_ENABLED=false` turns both off. Unset, it is on everywhere except ENV=test, so the rest of the
suite never writes to the developer's database; app/tests/test_analytics.py turns it on.
Properties stay small and carry no PII: ids, slugs, route templates and counters only.
"""

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from http.cookies import SimpleCookie
from typing import Annotated, Any, Literal

from fastapi import Request, Response
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    StringConstraints,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Select, insert, select
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from app.db import SessionLocal
from app.models import (
    Academy,
    ActivityEvent,
    Channel,
    LearningRoute,
    Lesson,
    Module,
    Post,
    RefreshToken,
    Resource,
    User,
)
from app.models.common import utcnow
from app.security import hash_token

logger = logging.getLogger("app.analytics")

REFRESH_COOKIE = "upx_refresh"  # app/routers/auth.py: login/register set it; we map it back to the user
MAX_EVENTS = 50
MAX_PROPERTIES_BYTES = 2048
CLOCK_SKEW = timedelta(minutes=5)  # client timestamps are clamped to now ± this
MAX_ID = 2**31 - 1
# A denylist of keys that usually carry personal data or free text. It cannot catch everything (a value under
# any other key may still hold an email): the client contract is "ids, slugs and counters only".
PII_KEYS = frozenset(
    {"email", "boleta", "password", "token", "name", "full_name", "nickname", "phone"}
    | {"query", "q", "search", "term", "text", "message", "body"}
)
RESERVED_KEYS = frozenset({"path"})  # set by the server from the validated `path` field


class AnalyticsSettings(BaseSettings):
    """Own settings (app/config.py belongs to another task)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)

    env: str = "dev"
    analytics_enabled: bool | None = None

    @property
    def enabled(self) -> bool:
        return self.env != "test" if self.analytics_enabled is None else self.analytics_enabled


@lru_cache
def get_analytics_settings() -> AnalyticsSettings:
    return AnalyticsSettings()


# Background writes open their own session (the request's one is closed by then). Tests swap it.
session_factory: Callable[[], Session] = SessionLocal


# ── Server events: route template + method → event ─────────


@dataclass(frozen=True)
class ServerEvent:
    name: str
    subject_type: str | None = None
    subject_param: str | None = None  # path parameter with the subject id (or the academy slug)
    property_params: tuple[str, ...] = ()  # path parameters copied into properties (never free text)
    user_from_cookie: bool = False  # login/register: no auth dependency ran, the new session names the user


SERVER_EVENTS: dict[tuple[str, str], ServerEvent] = {
    ("POST", "/api/auth/login"): ServerEvent("auth.login", user_from_cookie=True),
    ("POST", "/api/auth/register"): ServerEvent("auth.registered", user_from_cookie=True),
    ("GET", "/api/academies/{slug}/home"): ServerEvent("club.viewed", "academy", "slug"),
    ("POST", "/api/academies/{slug}/enroll"): ServerEvent("club.joined", "academy", "slug"),
    ("DELETE", "/api/academies/{slug}/enroll"): ServerEvent("club.left", "academy", "slug"),
    ("GET", "/api/routes/{route_id}"): ServerEvent("route.viewed", "route", "route_id"),
    ("GET", "/api/lessons/{lesson_id}"): ServerEvent("lesson.viewed", "lesson", "lesson_id"),
    ("POST", "/api/lessons/{lesson_id}/complete"): ServerEvent("lesson.completed", "lesson", "lesson_id"),
    ("POST", "/api/channels/{channel_id}/posts"): ServerEvent("post.created", "channel", "channel_id"),
    ("POST", "/api/posts/{post_id}/comments"): ServerEvent("comment.created", "post", "post_id"),
    ("PUT", "/api/posts/{post_id}/reactions/{kind}"): ServerEvent(
        "reaction.added", "post", "post_id", ("kind",)
    ),
    ("DELETE", "/api/posts/{post_id}/reactions/{kind}"): ServerEvent(
        "reaction.removed", "post", "post_id", ("kind",)
    ),
}

# Club (academy) that owns each kind of subject, so every event can be sliced per club.
ACADEMY_OF: dict[str, Callable[[int], Select]] = {
    "route": lambda i: select(LearningRoute.academy_id).where(LearningRoute.id == i),
    "lesson": lambda i: (
        select(LearningRoute.academy_id)
        .join(Module, Module.route_id == LearningRoute.id)
        .join(Lesson, Lesson.module_id == Module.id)
        .where(Lesson.id == i)
    ),
    "channel": lambda i: select(Channel.academy_id).where(Channel.id == i),
    "post": lambda i: (
        select(Channel.academy_id).join(Post, Post.channel_id == Channel.id).where(Post.id == i)
    ),
    "resource": lambda i: select(Resource.academy_id).where(Resource.id == i),
}


@dataclass
class PendingEvent:
    spec: ServerEvent
    occurred_at: datetime
    user_id: int | None
    path_params: dict[str, str] = field(default_factory=dict)
    refresh_token: str | None = None


def capture(request: Request, response: Response) -> None:
    """Middleware hook: schedule the server event for this request, if any. Never raises."""
    try:
        if not 200 <= response.status_code < 300 or not get_analytics_settings().enabled:
            return
        template = getattr(request.scope.get("route"), "path", None)
        spec = SERVER_EVENTS.get((request.method, template))
        if spec is None:
            return
        pending = PendingEvent(
            spec=spec,
            occurred_at=utcnow(),
            user_id=getattr(request.state, "user_id", None),
            path_params={k: str(v) for k, v in request.path_params.items()},
            refresh_token=_refresh_cookie(response) if spec.user_from_cookie else None,
        )
        attach(response, BackgroundTask(write_server_event, pending))
    except Exception:
        logger.exception("analytics: could not schedule %s %s", request.method, request.url.path)


def attach(response: Response, task: BackgroundTask) -> None:
    """Run `task` after the response is sent, after any background work the response already had."""
    previous = response.background
    response.background = task if previous is None else BackgroundTask(_run_both, previous, task)


async def _run_both(first: BackgroundTask, second: BackgroundTask) -> None:
    await first()
    await second()


def _refresh_cookie(response: Response) -> str | None:
    for header in response.headers.getlist("set-cookie"):
        cookie: SimpleCookie = SimpleCookie()
        cookie.load(header)  # malformed parts are skipped, never raised
        if REFRESH_COOKIE in cookie:
            return cookie[REFRESH_COOKIE].value
    return None


def write_server_event(pending: PendingEvent) -> None:
    """Background task (thread pool): one session, one INSERT statement, one commit. The user and club
    lookups are scalar subqueries inside that INSERT, so a write is a single short round trip that holds a
    pooled connection only for that long. Errors are logged, never raised."""
    try:
        with session_factory() as db:
            db.execute(insert(ActivityEvent).values(**server_values(pending)))
            db.commit()
    except Exception:
        logger.exception("analytics: could not record %s", pending.spec.name)


def server_values(pending: PendingEvent) -> dict[str, Any]:
    """Column values for one server event; ids that need a lookup are scalar subqueries."""
    spec = pending.spec
    user_id: Any = pending.user_id
    if spec.user_from_cookie and pending.refresh_token:
        token_hash = hash_token(pending.refresh_token)
        user_id = select(RefreshToken.user_id).where(RefreshToken.token_hash == token_hash).scalar_subquery()
    raw = pending.path_params.get(spec.subject_param or "")
    subject_id: Any = None
    if spec.subject_type == "academy" and raw:
        subject_id = select(Academy.id).where(Academy.slug == raw).scalar_subquery()
    elif raw and raw.isdigit() and int(raw) <= MAX_ID:
        subject_id = int(raw)
    return {
        "occurred_at": pending.occurred_at,
        "user_id": user_id,
        "academy_id": academy_expr(spec.subject_type, subject_id),
        "name": spec.name,
        "subject_type": spec.subject_type if subject_id is not None else None,
        "subject_id": subject_id,
        "properties": {
            key: pending.path_params[key] for key in spec.property_params if key in pending.path_params
        },
        "source": "server",
    }


def academy_expr(subject_type: str | None, subject_id: Any) -> Any:
    """Club of a subject: the id itself for an academy, a scalar subquery for lessons, posts..., else None."""
    if subject_type is None or subject_id is None:
        return None
    if subject_type == "academy":
        return subject_id
    query = ACADEMY_OF.get(subject_type)
    return query(subject_id).scalar_subquery() if query else None


# ── Web events: POST /api/analytics/events ──────────────────

WEB_EVENTS = (
    "page.view",
    "video.play",
    "video.pause",
    "video.ended",
    "video.progress",
    "search.performed",
    "resource.opened",
    "link.opened",
)
WebEventName = Literal[WEB_EVENTS]  # type: ignore[valid-type]
SubjectType = Literal["academy", "route", "lesson", "resource", "post", "channel", "project", "blog", "event"]
PropertyKey = Annotated[str, StringConstraints(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_.]+$")]
PropertyValue = str | int | FiniteFloat | bool | None  # NaN/Infinity are not JSON: 422, never a 500


class WebEventIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: WebEventName
    occurred_at: datetime | None = None
    path: str | None = Field(
        default=None, max_length=200, pattern=r"^/[A-Za-z0-9_\-/:.*]*$"
    )  # route template
    subject_type: SubjectType | None = None
    subject_id: int | None = Field(default=None, ge=1, le=MAX_ID)
    academy_slug: str | None = Field(default=None, max_length=60, pattern=r"^[a-z0-9-]+$")
    properties: dict[PropertyKey, PropertyValue] = Field(default_factory=dict)

    @field_validator("properties")
    @classmethod
    def _small_and_anonymous(cls, value: dict[str, Any]) -> dict[str, Any]:
        keys = {key.lower() for key in value}
        if PII_KEYS & keys:
            raise ValueError("properties must not carry personal data or free text")
        if RESERVED_KEYS & keys:
            raise ValueError("properties.path is reserved: send the route template in `path`")
        if len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()) > MAX_PROPERTIES_BYTES:
            raise ValueError(f"properties must be at most {MAX_PROPERTIES_BYTES} bytes")
        return value

    @model_validator(mode="after")
    def _subject_pair(self) -> "WebEventIn":
        if (self.subject_type is None) != (self.subject_id is None):
            raise ValueError("subject_type and subject_id go together")
        return self


class EventBatchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    events: list[WebEventIn] = Field(min_length=1, max_length=MAX_EVENTS)


class AcceptedOut(BaseModel):
    accepted: int


def clamp(moment: datetime | None, now: datetime) -> datetime:
    """Client clocks lie: keep the timestamp within now ± CLOCK_SKEW (naive values are UTC)."""
    if moment is None:
        return now
    moment = moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment.astimezone(UTC)
    return min(max(moment, now - CLOCK_SKEW), now + CLOCK_SKEW)


def record_web_events(db: Session, user: User, batch: EventBatchIn) -> int:
    if not get_analytics_settings().enabled:
        return 0
    now = utcnow()
    slugs = {event.academy_slug for event in batch.events if event.academy_slug}
    # Client-declared club: only existing slugs map to an id (else NULL), but which club is the client's word.
    academies = dict(db.execute(select(Academy.slug, Academy.id).where(Academy.slug.in_(slugs))).all())
    rows = []
    for event in batch.events:
        properties = dict(event.properties)
        if event.path:
            properties["path"] = event.path
        rows.append(
            ActivityEvent(
                occurred_at=clamp(event.occurred_at, now),
                user_id=user.id,
                academy_id=academies.get(event.academy_slug),
                name=event.name,
                subject_type=event.subject_type,
                subject_id=event.subject_id,
                properties=properties,
                session_id=batch.session_id,
                source="web",
            )
        )
    db.add_all(rows)
    db.commit()
    return len(rows)
