from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.common import CreatedAtMixin, UTCDateTime, utcnow


class Academy(CreatedAtMixin, Base):
    __tablename__ = "academies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(60), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    short_description: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    welcome_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String(500))
    mascot_url: Mapped[str | None] = mapped_column(String(500))
    color_primary: Mapped[str] = mapped_column(String(7), default="#00BF63", nullable=False)
    color_secondary: Mapped[str] = mapped_column(String(7), default="#04944F", nullable=False)
    color_accent: Mapped[str] = mapped_column(String(7), default="#F28034", nullable=False)
    color_accent_2: Mapped[str | None] = mapped_column(String(7))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # IDEA §6 "order"


class Enrollment(Base):
    __tablename__ = "enrollments"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    academy_id: Mapped[int] = mapped_column(
        ForeignKey("academies.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    enrolled_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utcnow, server_default=func.now(), nullable=False
    )
