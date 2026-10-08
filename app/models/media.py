"""Uploaded files kept in the database when MEDIA_STORAGE=database (UPS-030).

Hosts with an ephemeral disk (Render free) lose `/media` on every restart; the bytes live here instead,
under the same key as the disk path (`post/<uuid>.webp`), so stored URLs never change.
"""

from sqlalchemy import LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.common import CreatedAtMixin


class MediaObject(CreatedAtMixin, Base):
    __tablename__ = "media_objects"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    content_type: Mapped[str] = mapped_column(String(40), nullable=False)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
