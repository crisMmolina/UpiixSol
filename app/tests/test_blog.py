import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BlogPost

SLUG = "bienvenidos-a-upiixsol-campus"
NEW = {"title": "Taller de Git", "slug": "taller-git", "body": "Trae tu laptop."}


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (64, 40), (0, 191, 99)).save(buffer, "PNG")
    return buffer.getvalue()


@pytest.fixture
def post_id(db: Session, seeded: dict) -> int:
    return db.scalar(select(BlogPost.id).where(BlogPost.slug == SLUG))


def test_public_listing_and_detail_expose_only_public_author(client: TestClient, seeded: dict) -> None:
    items = client.get("/api/blog").json()["items"]
    assert SLUG in [p["slug"] for p in items] and len(items) == 6  # newest-first demo posts
    detail = client.get(f"/api/blog/{SLUG}").json()
    assert set(detail["author"]) == {"id", "nickname", "avatar_url"}  # never email or boleta


def test_draft_hidden_except_for_superadmin(
    as_superadmin: TestClient, client: TestClient, seeded: dict
) -> None:
    created = as_superadmin.post("/api/blog", json=NEW)
    assert created.status_code == 201 and created.json()["published_at"] is None
    assert created.json()["author"]["nickname"]
    assert client.get("/api/blog/taller-git").status_code == 404
    assert "taller-git" not in [p["slug"] for p in client.get("/api/blog").json()["items"]]
    assert as_superadmin.get("/api/blog/taller-git").status_code == 200
    drafts = as_superadmin.get("/api/blog", params={"drafts": True}).json()["items"]
    assert "taller-git" in [p["slug"] for p in drafts]


def test_publish_keeps_date_and_unpublish_hides(
    as_superadmin: TestClient, client: TestClient, seeded: dict
) -> None:
    post = as_superadmin.post("/api/blog", json={**NEW, "published": True}).json()
    assert post["published_at"] is not None
    again = as_superadmin.put(
        f"/api/blog/{post['id']}", json={**NEW, "title": "Nuevo", "published": True}
    ).json()
    assert again["published_at"] == post["published_at"] and again["title"] == "Nuevo"
    assert client.get("/api/blog/taller-git").status_code == 200
    as_superadmin.put(f"/api/blog/{post['id']}", json=NEW)
    assert client.get("/api/blog/taller-git").status_code == 404


def test_body_is_sanitized(as_superadmin: TestClient, seeded: dict) -> None:
    body = as_superadmin.post("/api/blog", json={**NEW, "body": '<img src=x onerror="alert(1)">hola'}).json()[
        "body"
    ]
    assert "onerror" not in body


def test_duplicate_slug_409_and_validation_422(as_superadmin: TestClient, seeded: dict) -> None:
    assert as_superadmin.post("/api/blog", json={**NEW, "slug": SLUG}).status_code == 409
    assert as_superadmin.post("/api/blog", json={**NEW, "title": ""}).status_code == 422
    assert as_superadmin.post("/api/blog", json={**NEW, "author_id": 1}).status_code == 422


def test_only_superadmin_writes(
    as_member: TestClient, as_admin_ia: TestClient, client: TestClient, post_id: int
) -> None:
    for c, code in ((client, 401), (as_member, 403), (as_admin_ia, 403)):
        assert c.post("/api/blog", json=NEW).status_code == code
        assert c.put(f"/api/blog/{post_id}", json=NEW).status_code == code
        assert c.delete(f"/api/blog/{post_id}").status_code == code
        assert (
            c.post(f"/api/blog/{post_id}/cover", files={"file": ("c.png", _png(), "image/png")}).status_code
            == code
        )


def test_cover_and_delete(as_superadmin: TestClient, post_id: int) -> None:
    first = as_superadmin.post(
        f"/api/blog/{post_id}/cover", files={"file": ("a.png", _png(), "image/png")}
    ).json()
    second = as_superadmin.post(
        f"/api/blog/{post_id}/cover", files={"file": ("b.png", _png(), "image/png")}
    ).json()
    assert second["author"] is not None
    assert as_superadmin.get(first["cover_url"]).status_code == 404
    assert as_superadmin.delete(f"/api/blog/{post_id}").status_code == 204
    assert as_superadmin.get(second["cover_url"]).status_code == 404


def test_cover_kept_when_commit_fails(
    as_superadmin: TestClient, db: Session, post_id: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = as_superadmin.post(
        f"/api/blog/{post_id}/cover", files={"file": ("a.png", _png(), "image/png")}
    ).json()

    def boom() -> None:
        raise RuntimeError("db down")

    monkeypatch.setattr(db, "commit", boom)
    assert (
        as_superadmin.post(
            f"/api/blog/{post_id}/cover", files={"file": ("b.png", _png(), "image/png")}
        ).status_code
        == 500
    )
    monkeypatch.undo()
    assert db.get(BlogPost, post_id).cover_url == first["cover_url"]


def test_missing_post_404(as_superadmin: TestClient) -> None:
    assert as_superadmin.put("/api/blog/9999", json=NEW).status_code == 404
    assert as_superadmin.delete("/api/blog/9999").status_code == 404
    assert as_superadmin.get("/api/blog/no-existe").status_code == 404
