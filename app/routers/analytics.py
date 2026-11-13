"""Client usage events (UPS-037): small validated batches from web/src/lib/analytics.ts.

    POST /api/analytics/events  {session_id, events: [{name, occurred_at?, path?, subject_type?, subject_id?,
                                 academy_slug?, properties?}]}  → 202 {accepted}

Signed-in users only, at most 50 events per batch and 2 KB of properties per event, names from
WEB_EVENTS (anything else is a 422), rate-limited per user. Server-side events are captured by the
middleware in app/main.py instead (see app/services/analytics.py).
"""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.ratelimit import limiter
from app.security import current_user
from app.services import analytics as service

router = APIRouter(prefix="/api/analytics", tags=["analytics"])
EVENTS_LIMIT = "30/minute"  # the tracker flushes every ~10 s or 20 events, plus once per page hide


def _per_user(request: Request) -> str:
    return f"analytics:{getattr(request.state, 'user_id', None)}"


@router.post("/events", response_model=service.AcceptedOut, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(EVENTS_LIMIT, key_func=_per_user)
def ingest_events(
    request: Request,
    batch: service.EventBatchIn,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> service.AcceptedOut:
    return service.AcceptedOut(accepted=service.record_web_events(db, user, batch))
