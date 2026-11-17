"""Opt-out endpoints (UPS-076, spec 003 §Opt-out): the public one-click unsubscribe and the preference.

`/unsubscribe` has no session: the token in the query string (`?t=`, the access log keeps only the path)
is the credential. The email footer links to the GET, which only hands over to the `/baja` page, because
mail scanners prefetch links; only the POST (RFC 8058 one-click, or the /baja page) suppresses.
"""

from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.ratelimit import limiter
from app.security import current_user
from app.services import mail_suppressions as service
from app.services.mail_suppressions import PreferencesIn, PreferencesOut

router = APIRouter(prefix="/api/mail", tags=["mail"])
UNSUBSCRIBE_LIMIT = "10/minute"  # per IP: stops guessing tokens


@router.get("/unsubscribe", include_in_schema=False)
def unsubscribe_link(t: Annotated[str | None, Query()] = None) -> RedirectResponse:
    target = f"/baja?t={quote(t, safe='')}" if t else "/baja"
    return RedirectResponse(target, status_code=303)  # changes nothing


@router.post("/unsubscribe")
@limiter.limit(UNSUBSCRIBE_LIMIT)
def unsubscribe(
    request: Request, t: Annotated[str | None, Query()] = None, db: Session = Depends(get_db)
) -> dict[str, bool]:
    # The body is never read: form-encoded (`List-Unsubscribe=One-Click`), JSON or empty all work.
    service.unsubscribe_by_token(db, t)
    db.commit()
    return {"unsubscribed": True}  # the same for a known, an unknown and a missing token


@router.get("/preferences", response_model=PreferencesOut)
def get_preferences(user: User = Depends(current_user), db: Session = Depends(get_db)) -> PreferencesOut:
    return service.get_preference(db, user)


@router.put("/preferences", response_model=PreferencesOut)
def put_preferences(
    data: PreferencesIn, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> PreferencesOut:
    result = service.set_preference(db, user, data.receive_club_email)
    db.commit()
    return result
