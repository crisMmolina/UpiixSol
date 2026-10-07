import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Academy, Channel, ChannelType, Comment, Post, Role
from app.tests.conftest import auth_headers, make_academy, make_user


def _channel(db: Session, slug: str) -> Channel:
    return db.scalar(select(Channel).where(Channel.slug == slug))


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (30, 30), (0, 191, 99)).save(buffer, "PNG")
    return buffer.getvalue()


def test_channels_list_feed_general_and_active_academies(as_member: TestClient, db: Session) -> None:
    inactive = make_academy(db, "dormida", "Dormida")
    inactive.is_active = False
    db.add(Channel(type=ChannelType.academy, academy_id=inactive.id, name="Dormida", slug="dormida"))
    db.flush()
    channels = as_member.get("/api/channels").json()
    assert [(c["slug"], c["type"]) for c in channels] == [
        ("feed", "feed"),
        ("general", "general"),
        ("upiixia", "academy"),
    ]


def test_post_in_academy_channel_appears_in_feed(as_member: TestClient, db: Session) -> None:
    channel = _channel(db, "upiixia")
    response = as_member.post(f"/api/channels/{channel.id}/posts", data={"body": "Encontré un dataset 🎉"})
    assert response.status_code == 201
    post = response.json()
    assert post["channel_slug"] == "upiixia" and post["author"]["nickname"] == "alumno.demo"

    feed = _channel(db, "feed")
    first = as_member.get(f"/api/channels/{feed.id}/posts").json()["items"][0]
    assert first["id"] == post["id"]
    own = as_member.get(f"/api/channels/{channel.id}/posts").json()["items"][0]
    assert own["id"] == post["id"]


def test_post_with_image_and_link(as_member: TestClient, db: Session) -> None:
    channel = _channel(db, "general")
    response = as_member.post(
        f"/api/channels/{channel.id}/posts",
        data={"body": "Mira esto", "link_url": "https://scikit-learn.org"},
        files={"image": ("foto.png", _png(), "image/png")},
    )
    body = response.json()
    assert response.status_code == 201
    assert body["image_url"].startswith("/media/post/") and body["link_url"] == "https://scikit-learn.org"


def test_post_validation(as_member: TestClient, db: Session) -> None:
    channel = _channel(db, "general")
    path = f"/api/channels/{channel.id}/posts"
    assert as_member.post(path, data={"body": ""}).status_code == 422
    assert as_member.post(path, data={"body": "x" * 5001}).status_code == 422
    assert as_member.post(path, data={"body": "hola", "link_url": "javascript:alert(1)"}).status_code == 422
    bad_image = as_member.post(path, data={"body": "hola"}, files={"image": ("x.png", b"nope", "image/png")})
    assert bad_image.status_code == 422
    sanitized = as_member.post(path, data={"body": "hola <script>alert(1)</script>"}).json()
    assert "<script" not in sanitized["body"]


def test_cannot_post_in_feed_or_inactive_or_unknown_channel(
    as_member: TestClient, db: Session, seeded: dict
) -> None:
    assert (
        as_member.post(f"/api/channels/{_channel(db, 'feed').id}/posts", data={"body": "x"}).status_code
        == 422
    )
    db.get(Academy, seeded["academy_id"]).is_active = False
    db.flush()
    channel = _channel(db, "upiixia")
    assert as_member.post(f"/api/channels/{channel.id}/posts", data={"body": "x"}).status_code == 404
    assert as_member.get(f"/api/channels/{channel.id}/posts").status_code == 404
    assert as_member.post("/api/channels/9999/posts", data={"body": "x"}).status_code == 404


def test_post_rate_limit_10_per_minute(as_member: TestClient, db: Session) -> None:
    path = f"/api/channels/{_channel(db, 'general').id}/posts"
    statuses = [as_member.post(path, data={"body": f"post {i}"}).status_code for i in range(11)]
    assert statuses[:10] == [201] * 10 and statuses[10] == 429


def test_responses_never_expose_pii(as_member: TestClient, db: Session) -> None:
    feed = _channel(db, "feed")
    text = as_member.get(f"/api/channels/{feed.id}/posts").text
    assert "@upiixsol.dev" not in text and "2026000001" not in text


def test_posts_paginate_newest_first(as_member: TestClient, db: Session, seeded: dict) -> None:
    channel = _channel(db, "upiixia")
    first = as_member.get(f"/api/channels/{channel.id}/posts?limit=2").json()
    second = as_member.get(f"/api/channels/{channel.id}/posts?limit=2&cursor={first['next_cursor']}").json()
    third = as_member.get(f"/api/channels/{channel.id}/posts?limit=2&cursor={second['next_cursor']}").json()
    items = first["items"] + second["items"] + third["items"]
    assert len(items) == 5 and third["next_cursor"] is None
    stamps = [p["created_at"] for p in items]
    assert stamps == sorted(stamps, reverse=True)


def test_comments_create_list_and_count(as_member: TestClient, db: Session) -> None:
    post = db.scalars(select(Post)).first()
    created = as_member.post(f"/api/posts/{post.id}/comments", json={"body": "¡Gracias! <b>útil</b>"})
    assert created.status_code == 201 and created.json()["author"]["nickname"] == "alumno.demo"
    as_member.post(f"/api/posts/{post.id}/comments", json={"body": "Otro"})
    page = as_member.get(f"/api/posts/{post.id}/comments").json()
    assert [c["body"] for c in page["items"]][1] == "Otro"  # oldest first
    feed_post = next(
        p
        for p in as_member.get(f"/api/channels/{_channel(db, 'feed').id}/posts?limit=50").json()["items"]
        if p["id"] == post.id
    )
    assert feed_post["comment_count"] == 2
    assert as_member.post(f"/api/posts/{post.id}/comments", json={"body": ""}).status_code == 422
    assert as_member.post("/api/posts/9999/comments", json={"body": "x"}).status_code == 404


def test_hide_audit(as_admin_ia: TestClient, as_member: TestClient, db: Session, seeded: dict) -> None:
    post = db.scalar(select(Post).where(Post.channel_id == _channel(db, "upiixia").id))
    response = as_admin_ia.post(f"/api/posts/{post.id}/hide")
    assert response.status_code == 200
    db.refresh(post)
    assert post.is_hidden and post.hidden_by_id == seeded["admin_ia_id"] and post.hidden_at is not None
    ids = [
        p["id"]
        for p in as_member.get(f"/api/channels/{_channel(db, 'feed').id}/posts?limit=50").json()["items"]
    ]
    assert post.id not in ids
    assert as_member.get(f"/api/posts/{post.id}/comments").status_code == 404


def test_moderation_scope(
    as_admin_ia: TestClient, as_member: TestClient, as_superadmin: TestClient, db: Session
) -> None:
    general_post = Post(
        channel_id=_channel(db, "general").id, author_id=db.scalars(select(Post)).first().author_id, body="x"
    )
    db.add(general_post)
    db.flush()
    assert as_member.post(f"/api/posts/{general_post.id}/hide").status_code == 403
    assert as_admin_ia.post(f"/api/posts/{general_post.id}/hide").status_code == 403  # not their channel
    assert as_superadmin.post(f"/api/posts/{general_post.id}/hide").status_code == 200
    assert as_superadmin.post("/api/posts/9999/hide").status_code == 404


def test_hide_comment(as_admin_ia: TestClient, as_member: TestClient, db: Session, seeded: dict) -> None:
    post = db.scalar(select(Post).where(Post.channel_id == _channel(db, "upiixia").id))
    comment = Comment(post_id=post.id, author_id=seeded["member_id"], body="spam")
    db.add(comment)
    db.flush()
    assert as_member.post(f"/api/comments/{comment.id}/hide").status_code == 403
    assert as_admin_ia.post(f"/api/comments/{comment.id}/hide").status_code == 200
    db.refresh(comment)
    assert comment.is_hidden and comment.hidden_by_id == seeded["admin_ia_id"]
    assert as_member.get(f"/api/posts/{post.id}/comments").json()["items"] == []
    assert as_admin_ia.post("/api/comments/9999/hide").status_code == 404


def test_other_academy_admin_cannot_moderate(client: TestClient, db: Session) -> None:
    robo = make_academy(db, "robotica", "Robótica")
    robo_admin = make_user(db, role=Role.academy_admin, email="robo@upiixsol.dev", academy_id=robo.id)
    post = db.scalars(select(Post)).first()
    assert client.post(f"/api/posts/{post.id}/hide", headers=auth_headers(robo_admin)).status_code == 403


def test_community_requires_login(client: TestClient) -> None:
    assert client.get("/api/channels").status_code == 401
    assert client.get("/api/channels/1/posts").status_code == 401


@pytest.fixture(autouse=True)
def _seed(seeded: dict) -> None:
    """Every test in this module runs on the demo seed (channels + 5 posts)."""


def test_failed_post_removes_uploaded_image(
    as_member: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pathlib import Path

    from app.config import get_settings

    folder = Path(get_settings().media_dir) / "post"
    before = set(folder.iterdir()) if folder.exists() else set()

    def boom() -> None:
        raise RuntimeError("db down")

    monkeypatch.setattr(db, "commit", boom)
    response = as_member.post(
        f"/api/channels/{_channel(db, 'general').id}/posts",
        data={"body": "con foto"},
        files={"image": ("f.png", _png(), "image/png")},
    )
    assert response.status_code == 500
    assert (set(folder.iterdir()) if folder.exists() else set()) == before


def test_oversized_body_is_rejected_before_parsing(as_member: TestClient, db: Session) -> None:
    """Security review UPS-011: a huge multipart body must not be spooled before any check."""
    from app.body_limit import MAX_BODY_BYTES

    path = f"/api/channels/{_channel(db, 'general').id}/posts"
    big = b"x" * (MAX_BODY_BYTES + 1)
    response = as_member.post(path, data={"body": "x"}, files={"image": ("big.png", big, "image/png")})
    assert response.status_code == 413 and response.json()["error"]["code"] == "payload_too_large"


def test_streamed_body_over_limit_is_cut(as_member: TestClient, db: Session) -> None:
    from app.body_limit import MAX_BODY_BYTES

    path = f"/api/channels/{_channel(db, 'general').id}/posts"

    def chunks():
        for _ in range(7):
            yield b"y" * (MAX_BODY_BYTES // 6)

    response = as_member.post(
        path, content=chunks(), headers={"Content-Type": "multipart/form-data; boundary=zzz"}
    )
    assert response.status_code == 413


def test_cannot_moderate_comment_under_hidden_post(
    as_admin_ia: TestClient, db: Session, seeded: dict
) -> None:
    post = db.scalar(select(Post).where(Post.channel_id == _channel(db, "upiixia").id))
    comment = Comment(post_id=post.id, author_id=seeded["member_id"], body="x")
    db.add(comment)
    post.is_hidden = True
    db.flush()
    assert as_admin_ia.post(f"/api/comments/{comment.id}/hide").status_code == 404


def test_body_limit_passes_through_disconnect_messages() -> None:
    import asyncio

    from app.body_limit import BodySizeLimitMiddleware

    seen: list[str] = []

    async def inner(scope, receive, send) -> None:
        seen.append((await receive())["type"])

    async def receive():
        return {"type": "http.disconnect"}

    async def send(_message) -> None:
        return None

    asyncio.run(BodySizeLimitMiddleware(inner)({"type": "http", "headers": []}, receive, send))
    assert seen == ["http.disconnect"]
