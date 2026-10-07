"""Contract smoke tests: every schema validates its happy path and rejects the obvious bad input."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models import Channel, ChannelType, LessonProgress, Post, User
from app.schemas.academies import AcademyCreateIn, AcademyUpdateIn, HomeContentIn
from app.schemas.common import Page, ReorderIn
from app.schemas.community import ChannelOut, CommentIn, PostIn, PostOut
from app.schemas.content import BlogPostIn, EventIn, ProjectIn, ResourceIn
from app.schemas.learning import LessonIn, ModuleIn, RouteIn
from app.schemas.users import (
    AdminUserCreateIn,
    EmailChangeIn,
    PasswordChangeIn,
    ProfileUpdateIn,
    PublicUser,
    UserMe,
)
from app.services.progress import mark_viewed


def test_public_user_never_exposes_pii(member: User) -> None:
    dumped = PublicUser.model_validate(member).model_dump()
    assert set(dumped) == {"id", "nickname", "avatar_url"}
    assert UserMe.model_validate(member).boleta == "2026000001"


def test_post_out_from_orm(db: Session, member: User) -> None:
    channel = Channel(type=ChannelType.general, name="General", slug="general")
    db.add(channel)
    db.flush()
    post = Post(channel_id=channel.id, author_id=member.id, body="hola")
    db.add(post)
    db.flush()
    out = PostOut(
        id=post.id,
        channel_id=channel.id,
        author=PublicUser.model_validate(member),
        body=post.body,
        image_url=None,
        link_url=None,
        created_at=post.created_at,
    )
    assert "email" not in out.model_dump_json()
    assert ChannelOut.model_validate(channel).type == ChannelType.general


def test_event_requires_end_after_start() -> None:
    start = datetime(2026, 10, 10, 17, tzinfo=UTC)
    assert EventIn(title="Taller", starts_at=start, ends_at=start + timedelta(hours=2)).academy_id is None
    with pytest.raises(ValidationError):
        EventIn(title="Taller", starts_at=start, ends_at=start - timedelta(minutes=1))


def test_inputs_happy_path_and_extra_fields_rejected() -> None:
    samples = [
        (AcademyCreateIn, {"slug": "upiixrobotica", "name": "UpiixRobótica"}),
        (AcademyUpdateIn, {"is_active": False}),
        (HomeContentIn, {"hero_title": "Hola"}),
        (ReorderIn, {"ids": [3, 1, 2]}),
        (PostIn, {"body": "hola", "link_url": "https://a.mx"}),
        (CommentIn, {"body": "ok"}),
        (ResourceIn, {"type": "link", "title": "Docs", "url": "https://docs.python.org"}),
        (ProjectIn, {"title": "Bot", "slug": "bot"}),
        (BlogPostIn, {"title": "Hola", "slug": "hola"}),
        (RouteIn, {"title": "Ruta"}),
        (ModuleIn, {"title": "Módulo"}),
        (LessonIn, {"title": "Clase", "youtube_url": "https://youtu.be/dQw4w9WgXcQ"}),
        (ProfileUpdateIn, {"nickname": "ana"}),
        (EmailChangeIn, {"new_email": "Ana@IPN.mx", "current_password": "x"}),
        (
            PasswordChangeIn,
            {"current_password": "x", "new_password": "12345678", "confirm_password": "12345678"},
        ),
        (
            AdminUserCreateIn,
            {
                "role": "academy_admin",
                "email": "a@ipn.mx",
                "full_name": "Ana López",
                "password": "12345678",
                "academy_id": 1,
            },
        ),
    ]
    for model, data in samples:
        model(**data)
        with pytest.raises(ValidationError):
            model(**data, unexpected="x")


@pytest.mark.parametrize(
    ("model", "data"),
    [
        (AcademyCreateIn, {"slug": "Upiix IA", "name": "x"}),
        (PostIn, {"body": ""}),
        (ReorderIn, {"ids": []}),
        (
            AdminUserCreateIn,
            {"role": "superadmin", "email": "a@ipn.mx", "full_name": "Ana López", "password": "12345678"},
        ),
        (LessonIn, {"title": "Clase", "youtube_url": "u", "duration_min": 0}),
    ],
)
def test_inputs_reject_bad_values(model, data: dict) -> None:
    with pytest.raises(ValidationError):
        model(**data)


def test_page_is_generic() -> None:
    assert Page[int](items=[1, 2]).next_cursor is None


def test_mark_viewed_creates_row_without_completing(db: Session, member: User, academy) -> None:
    from app.models import LearningRoute, Lesson, Module

    route = LearningRoute(academy_id=academy.id, title="R", is_published=True)
    db.add(route)
    db.flush()
    module = Module(route_id=route.id, title="M")
    db.add(module)
    db.flush()
    lesson = Lesson(module_id=module.id, title="L", youtube_url="u", youtube_video_id="dQw4w9WgXcQ")
    db.add(lesson)
    db.flush()
    row = mark_viewed(db, member.id, lesson.id)
    assert row.last_viewed_at is not None and row.completed_at is None
    assert db.get(LessonProgress, (member.id, lesson.id)) is row
