from datetime import timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import Channel, ChannelType, Post, User
from app.models.common import utcnow
from app.pagination import CursorParam, LimitParam, decode_cursor, encode_cursor, paginate


@pytest.fixture
def posts(db: Session, member: User) -> list[Post]:
    channel = Channel(type=ChannelType.general, name="General", slug="general")
    db.add(channel)
    db.flush()
    base = utcnow()
    rows = [
        Post(
            channel_id=channel.id,
            author_id=member.id,
            body=f"p{i}",
            created_at=base - timedelta(minutes=i % 3),
        )
        for i in range(7)
    ]  # repeated timestamps: the id breaks ties
    db.add_all(rows)
    db.flush()
    return rows


def _walk(db: Session, limit: int, descending: bool = True) -> list[list[int]]:
    pages, cursor = [], None
    while True:
        page = paginate(
            db,
            select(Post),
            [Post.created_at, Post.id],
            cursor=cursor,
            limit=limit,
            descending=descending,
            transform=lambda p: p.id,
        )
        pages.append(page.items)
        cursor = page.next_cursor
        if cursor is None:
            return pages


def test_pages_cover_everything_once_in_order(db: Session, posts: list[Post]) -> None:
    pages = _walk(db, limit=3)
    assert [len(p) for p in pages] == [3, 3, 1]
    flat = [i for page in pages for i in page]
    expected = [p.id for p in sorted(posts, key=lambda p: (p.created_at, p.id), reverse=True)]
    assert flat == expected


def test_ascending_and_exact_fit(db: Session, posts: list[Post]) -> None:
    pages = _walk(db, limit=7, descending=False)
    assert len(pages) == 1 and len(pages[0]) == 7


def test_limit_is_clamped_to_50(db: Session, posts: list[Post]) -> None:
    page = paginate(db, select(Post), [Post.id], cursor=None, limit=500)
    assert len(page.items) == 7
    page = paginate(db, select(Post), [Post.id], cursor=None, limit=0)
    assert len(page.items) == 1


def test_cursor_roundtrip_and_invalid_cursor() -> None:
    now = utcnow()
    assert decode_cursor(encode_cursor([now, 5]), [Post.created_at, Post.id]) == [now, 5]
    for bad in ("%%%", encode_cursor([1]), encode_cursor({"a": 1}), encode_cursor(["not-a-date", 1])):  # type: ignore[arg-type]
        with pytest.raises(AppError) as error:
            decode_cursor(bad, [Post.created_at, Post.id])
        assert error.value.status == 422


def test_query_params_reject_limit_over_50() -> None:
    app = FastAPI()

    @app.get("/items")
    def items(cursor: CursorParam = None, limit: LimitParam = 20) -> dict:
        return {"limit": limit, "cursor": cursor}

    client = TestClient(app)
    assert client.get("/items").json() == {"limit": 20, "cursor": None}
    assert client.get("/items?limit=51").status_code == 422
    assert client.get("/items?limit=0").status_code == 422
