import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Project, ProjectStatus

NEW = {
    "title": "Dron de reparto",
    "slug": "dron-reparto",
    "summary": "Prototipo",
    "body": "Hola",
    "tags": ["IoT"],
}


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (64, 40), (0, 191, 99)).save(buffer, "PNG")
    return buffer.getvalue()


@pytest.fixture
def draft(db: Session, seeded: dict) -> Project:
    project = Project(title="Secreto", slug="secreto", status=ProjectStatus.draft)
    db.add(project)
    db.flush()
    return project


def test_draft_project_not_listed(client: TestClient, draft: Project) -> None:
    slugs = [p["slug"] for p in client.get("/api/projects").json()["items"]]
    assert "secreto" not in slugs and len(slugs) == 3


def test_public_listing_is_anonymous_and_newest_first(client: TestClient, db: Session, seeded: dict) -> None:
    body = client.get("/api/projects", params={"limit": 2}).json()
    assert len(body["items"]) == 2 and body["next_cursor"]
    rest = client.get("/api/projects", params={"limit": 2, "cursor": body["next_cursor"]}).json()
    assert len(rest["items"]) == 1 and rest["next_cursor"] is None


def test_filter_by_tag(client: TestClient, seeded: dict) -> None:
    items = client.get("/api/projects", params={"tag": "vision"}).json()["items"]
    assert [p["slug"] for p in items] == ["clasificador-residuos"]
    assert client.get("/api/projects", params={"tag": "%"}).json()["items"] == []


def test_detail_by_slug_and_draft_404(client: TestClient, as_superadmin: TestClient, draft: Project) -> None:
    assert client.get("/api/projects/bot-horarios").json()["title"] == "Bot de horarios UPIIZ"
    assert client.get("/api/projects/secreto").status_code == 404
    assert client.get("/api/projects/no-existe").status_code == 404
    assert as_superadmin.get("/api/projects/secreto").status_code == 200


def test_drafts_listed_only_for_superadmin(
    as_superadmin: TestClient, as_member: TestClient, draft: Project
) -> None:
    super_slugs = [
        p["slug"] for p in as_superadmin.get("/api/projects", params={"drafts": True}).json()["items"]
    ]
    member_slugs = [
        p["slug"] for p in as_member.get("/api/projects", params={"drafts": True}).json()["items"]
    ]
    assert "secreto" in super_slugs and "secreto" not in member_slugs


def test_superadmin_creates_publishes_and_unpublishes(as_superadmin: TestClient, client: TestClient) -> None:
    created = as_superadmin.post("/api/projects", json={**NEW, "body": "<script>x</script>**ok**"})
    assert created.status_code == 201
    project = created.json()
    assert project["status"] == "draft" and project["published_at"] is None
    assert "<script>" not in project["body"] and project["tags"] == ["iot"]
    published = as_superadmin.put(
        f"/api/projects/{project['id']}", json={**NEW, "status": "published"}
    ).json()
    assert published["published_at"] is not None
    assert client.get("/api/projects/dron-reparto").status_code == 200
    again = as_superadmin.put(f"/api/projects/{project['id']}", json={**NEW, "status": "published"}).json()
    assert again["published_at"] == published["published_at"]  # first publication date is kept
    back = as_superadmin.put(f"/api/projects/{project['id']}", json={**NEW, "status": "draft"}).json()
    assert back["published_at"] is None
    assert client.get("/api/projects/dron-reparto").status_code == 404


def test_duplicate_slug_409(as_superadmin: TestClient, seeded: dict) -> None:
    response = as_superadmin.post("/api/projects", json={**NEW, "slug": "bot-horarios"})
    assert response.status_code == 409


def test_unknown_academy_422_and_bad_input_422(as_superadmin: TestClient, seeded: dict) -> None:
    assert as_superadmin.post("/api/projects", json={**NEW, "academy_id": 999}).status_code == 422
    assert as_superadmin.post("/api/projects", json={**NEW, "slug": "Con Espacios"}).status_code == 422
    assert as_superadmin.post("/api/projects", json={**NEW, "role": "x"}).status_code == 422


def test_only_superadmin_writes(
    as_member: TestClient, as_admin_ia: TestClient, client: TestClient, db: Session
) -> None:
    project_id = db.scalar(select(Project.id).where(Project.slug == "bot-horarios"))
    for c, code in ((client, 401), (as_member, 403), (as_admin_ia, 403)):
        assert c.post("/api/projects", json=NEW).status_code == code
        assert c.put(f"/api/projects/{project_id}", json=NEW).status_code == code
        assert c.delete(f"/api/projects/{project_id}").status_code == code
        files = {"file": ("c.png", _png(), "image/png")}
        assert c.post(f"/api/projects/{project_id}/cover", files=files).status_code == code


def test_cover_upload_replace_and_delete(as_superadmin: TestClient, db: Session, seeded: dict) -> None:
    project_id = db.scalar(select(Project.id).where(Project.slug == "bot-horarios"))
    first = as_superadmin.post(
        f"/api/projects/{project_id}/cover", files={"file": ("a.png", _png(), "image/png")}
    )
    second = as_superadmin.post(
        f"/api/projects/{project_id}/cover", files={"file": ("b.png", _png(), "image/png")}
    )
    old, new = first.json()["cover_url"], second.json()["cover_url"]
    assert old.startswith("/media/cover/") and old != new
    assert as_superadmin.get(old).status_code == 404 and as_superadmin.get(new).status_code == 200
    assert as_superadmin.delete(f"/api/projects/{project_id}").status_code == 204
    assert as_superadmin.get(new).status_code == 404
    assert as_superadmin.get("/api/projects/bot-horarios").status_code == 404


def test_cover_kept_when_commit_fails(
    as_superadmin: TestClient, db: Session, seeded: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_id = db.scalar(select(Project.id).where(Project.slug == "bot-horarios"))
    first = as_superadmin.post(
        f"/api/projects/{project_id}/cover", files={"file": ("a.png", _png(), "image/png")}
    )

    def boom() -> None:
        raise RuntimeError("db down")

    monkeypatch.setattr(db, "commit", boom)
    files = {"file": ("b.png", _png(), "image/png")}
    assert as_superadmin.post(f"/api/projects/{project_id}/cover", files=files).status_code == 500
    monkeypatch.undo()
    assert db.get(Project, project_id).cover_url == first.json()["cover_url"]


def test_missing_project_404(as_superadmin: TestClient) -> None:
    assert as_superadmin.put("/api/projects/9999", json=NEW).status_code == 404
    assert as_superadmin.delete("/api/projects/9999").status_code == 404


def test_tags_normalized_accent_free_and_bounded(as_superadmin: TestClient, client: TestClient) -> None:
    created = as_superadmin.post(
        "/api/projects", json={**NEW, "tags": ["Robótica IA", "robotica-ia", " "], "status": "published"}
    )
    assert created.json()["tags"] == ["robotica-ia"]
    assert [
        p["slug"] for p in client.get("/api/projects", params={"tag": "Robótica IA"}).json()["items"]
    ] == ["dron-reparto"]
    too_long = as_superadmin.post("/api/projects", json={**NEW, "slug": "otro", "tags": ["x" * 41]})
    assert too_long.status_code == 422 and too_long.json()["error"]["code"] == "invalid_tag"


def test_out_of_range_ids_422(as_superadmin: TestClient) -> None:
    assert as_superadmin.put(f"/api/projects/{10**30}", json=NEW).status_code == 422
    assert as_superadmin.delete(f"/api/blog/{10**30}").status_code == 422
