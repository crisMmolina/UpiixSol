"""Site brand (UPS-041): campus name, logo, mascot and wordmark colors, edited by superadmins in /admin."""

from datetime import datetime

from sqlalchemy import Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.common import UTCDateTime, utcnow


class SiteSettings(Base):
    """Singleton row (id = 1).

    `logo_url` None → the name drawn as a three-color wordmark; `mascot_url` None → no mascot anywhere.
    """

    __tablename__ = "site_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String(500))
    mascot_url: Mapped[str | None] = mapped_column(String(500))
    color_primary: Mapped[str] = mapped_column(String(7), nullable=False)
    color_secondary: Mapped[str] = mapped_column(String(7), nullable=False)
    color_accent: Mapped[str] = mapped_column(String(7), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utcnow, onupdate=utcnow, server_default=func.now(), nullable=False
    )
