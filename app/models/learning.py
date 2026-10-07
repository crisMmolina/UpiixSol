from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.common import CreatedAtMixin, UTCDateTime


class LearningRoute(CreatedAtMixin, Base):
    __tablename__ = "learning_routes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    academy_id: Mapped[int] = mapped_column(
        ForeignKey("academies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    cover_url: Mapped[str | None] = mapped_column(String(500))
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    modules: Mapped[list["Module"]] = relationship(
        back_populates="route",
        order_by="(Module.position, Module.id)",
        lazy="raise",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Module(Base):
    __tablename__ = "modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    route_id: Mapped[int] = mapped_column(
        ForeignKey("learning_routes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    route: Mapped[LearningRoute] = relationship(back_populates="modules", lazy="raise")
    lessons: Mapped[list["Lesson"]] = relationship(
        back_populates="module",
        order_by="(Lesson.position, Lesson.id)",
        lazy="raise",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Lesson(CreatedAtMixin, Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    module_id: Mapped[int] = mapped_column(
        ForeignKey("modules.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    youtube_url: Mapped[str] = mapped_column(String(300), nullable=False)
    youtube_video_id: Mapped[str] = mapped_column(
        String(11), nullable=False
    )  # derived (app/services/youtube.py)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)  # sanitized markdown
    duration_min: Mapped[int | None] = mapped_column(Integer)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    module: Mapped[Module] = relationship(back_populates="lessons", lazy="raise")
    links: Mapped[list["LessonLink"]] = relationship(
        back_populates="lesson",
        order_by="(LessonLink.position, LessonLink.id)",
        lazy="raise",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class LessonLink(Base):
    __tablename__ = "lesson_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lesson_id: Mapped[int] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"), index=True, nullable=False
    )
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    lesson: Mapped[Lesson] = relationship(back_populates="links", lazy="raise")


class LessonProgress(Base):
    """One row per (user, lesson). Primary key (user_id, lesson_id) doubles as the user_id index."""

    __tablename__ = "lesson_progress"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    lesson_id: Mapped[int] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    last_viewed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
