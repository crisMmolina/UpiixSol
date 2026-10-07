from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.common import CreatedAtMixin, Role, enum_check, str_enum


class User(CreatedAtMixin, Base):
    __tablename__ = "users"
    __table_args__ = (enum_check("role", Role),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role: Mapped[Role] = mapped_column(str_enum(Role), nullable=False, default=Role.member)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True, nullable=False)  # lowercase
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    nickname: Mapped[str] = mapped_column(String(40), nullable=False)
    boleta: Mapped[str | None] = mapped_column(String(10), unique=True, index=True, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    # Only for academy_admin: the single academy they manage.
    academy_id: Mapped[int | None] = mapped_column(
        ForeignKey("academies.id", ondelete="SET NULL"), index=True, nullable=True
    )
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    academy = relationship("Academy", foreign_keys=[academy_id], lazy="raise")


class RefreshToken(CreatedAtMixin, Base):
    """Refresh tokens are stored hashed; a family is revoked when a used token is replayed."""

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    family_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
