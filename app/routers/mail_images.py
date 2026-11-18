"""Email image upload (UPS-088, spec 004 §Images): a PNG/JPEG copy under /media/mail, public by URL."""

from fastapi import APIRouter, Depends, File, Request, UploadFile
from pydantic import BaseModel

from app.config import get_settings
from app.models import Role, User
from app.ratelimit import limiter
from app.security import require_role
from app.services import media

router = APIRouter(prefix="/api/mail", tags=["mail"])
IMAGE_LIMIT = "20/minute"  # decoding and re-encoding a 5 MB image is the costly part (plan.md §STRIDE, DoS)


class ImageOut(BaseModel):
    url: str


def _per_user(request: Request) -> str:
    return f"user:{getattr(request.state, 'user_id', None)}"


@router.post("/images", response_model=ImageOut, status_code=201)
@limiter.limit(IMAGE_LIMIT, key_func=_per_user)
async def upload_mail_image(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(require_role(Role.superadmin, Role.academy_admin)),
) -> ImageOut:
    url = await media.save_upload(file, "mail")
    return ImageOut(url=f"{get_settings().public_base_url.rstrip('/')}{url}")
