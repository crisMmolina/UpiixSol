"""Public Mailgun webhook (UPS-077, spec 003 §History and delivery status).

No session and no CSRF header: Mailgun's HMAC signature is the only credential. Anything that does not verify
gets the same 403 and changes nothing; everything that verifies gets 200 (an error makes Mailgun retry).
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.services import mail_webhooks as service

router = APIRouter(prefix="/api/mail/webhooks", tags=["mail"])


@router.post("/mailgun")
async def mailgun(request: Request, db: Session = Depends(get_db)) -> dict[str, bool]:
    try:
        body = await request.json()
    except ValueError:
        body = None
    event = service.verify(body)
    if event is None:
        service.log.warning("mail webhook rejected")
        raise HTTPException(status_code=403, detail="Firma inválida")
    service.apply_event(db, event)
    db.commit()
    return {"ok": True}
