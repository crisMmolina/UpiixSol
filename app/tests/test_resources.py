import io

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Academy, Resource, ResourceType
from app.tests.conftest import make_academy

LINK = "https://scikit-learn.org/stable/"


@pytest.fixture
def ia(seeded: dict, db: Session) -> Academy:
    return db.get(Academy, seeded["academy_id"])


@pytest.fixture
def other(db: Session, seeded: dict) -> Academy:
    return make_academy(db, "robotica", "UpiixRobótica")


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (40, 40), (0, 191, 99)).save(buffer, "PNG")
    return buffer.getvalue()


def _add(db: Session, academy: Academy, kind: ResourceType = ResourceType.link, title: str = "R") -> Resource:
    resource = Resource(academy_id=academy.id, type=kind, title=title, url=LINK)
    db.add(resource)
    db.flush()
    return resource


def _create(client: TestClient, academy_id: int, files: dict | None = None, **data: str) -> Response:
    return client.post(f"/api/academies/{academy_id}/resources", data=data, files=files)


def _upload(client: TestClient, resource_id: int) -> Response:
    return client.post(f"/api/resources/{resource_id}/file", files={"file": ("a.png", _png(), "image/png")})


def _list(client: TestClient, slug: str, **params: str | int) -> Response:
    return client.get(f"/api/academies/{slug}/resources", params=params)


# ── Scope ────────────────────────────────────────────────────


def test_admin_other_academy_cannot_create_resource_403(as_admin_ia: TestClient, other: Academy) -> None:
    assert _create(as_admin_ia, other.id, type="link", title="x", url=LINK).status_code == 403


def test_admin_other_academy_cannot_edit_delete_or_upload_403(
    as_admin_ia: TestClient, other: Academy, db: Session
) -> None:
    resource = _add(db, other)
    attempts = [
        as_admin_ia.patch(f"/api/resources/{resource.id}", json={"title": "x"}),
        as_admin_ia.delete(f"/api/resources/{resource.id}"),
        _upload(as_admin_ia, resource.id),
    ]
    assert [r.status_code for r in attempts] == [403] * len(attempts)
    assert db.get(Resource, resource.id).title == "R"


def test_member_cannot_create_resource_403(as_member: TestClient, ia: Academy) -> None:
    assert _create(as_member, ia.id, type="link", title="x", url=LINK).status_code == 403


def test_anonymous_gets_401(client: TestClient, ia: Academy) -> None:
    assert _list(client, ia.slug).status_code == 401
    assert _create(client, ia.id, type="link", title="x", url=LINK).status_code == 401


def test_superadmin_can_create_in_any_academy(as_superadmin: TestClient, other: Academy) -> None:
    response = _create(as_superadmin, other.id, type="video", title="Clase", url=LINK)
    assert response.status_code == 201
    assert response.json()["academy_id"] == other.id


def test_create_in_missing_academy_404(as_superadmin: TestClient) -> None:
    assert _create(as_superadmin, 9999, type="link", title="x", url=LINK).status_code == 404


# ── Listing ──────────────────────────────────────────────────


def test_member_lists_seeded_resources(as_member: TestClient, ia: Academy) -> None:
    response = _list(as_member, ia.slug)
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 3
    assert {item["type"] for item in items} == {"document", "link", "video"}


def test_list_filters_by_type(as_member: TestClient, ia: Academy) -> None:
    assert [item["type"] for item in _list(as_member, ia.slug, type="video").json()["items"]] == ["video"]


def test_list_rejects_unknown_type_422(as_member: TestClient, ia: Academy) -> None:
    assert _list(as_member, ia.slug, type="pdf").status_code == 422


def test_list_is_paginated_newest_first(as_member: TestClient, ia: Academy, db: Session) -> None:
    for i in range(3):
        _add(db, ia, title=f"extra {i}")
    first = _list(as_member, ia.slug, limit=4).json()
    assert len(first["items"]) == 4 and first["next_cursor"]
    second = _list(as_member, ia.slug, limit=4, cursor=first["next_cursor"]).json()
    assert len(second["items"]) == 2 and second["next_cursor"] is None
    ids = [item["id"] for item in first["items"] + second["items"]]
    assert ids == sorted(ids, reverse=True)


def test_list_only_returns_that_academy(as_member: TestClient, other: Academy, db: Session) -> None:
    _add(db, other, title="Robots")
    assert [item["title"] for item in _list(as_member, other.slug).json()["items"]] == ["Robots"]


def test_list_unknown_academy_404(as_member: TestClient) -> None:
    assert _list(as_member, "no-existe").status_code == 404


def test_list_inactive_academy_hidden_from_member(as_member: TestClient, other: Academy, db: Session) -> None:
    other.is_active = False
    db.flush()
    assert _list(as_member, other.slug).status_code == 404


# ── Create / edit / delete ───────────────────────────────────


def test_admin_creates_link_resource_with_clean_description(as_admin_ia: TestClient, ia: Academy) -> None:
    evil = "Hola <script>alert(1)</script>"
    response = _create(as_admin_ia, ia.id, type="link", title=" Guía ", description=evil, url=LINK)
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Guía"
    assert "<script>" not in body["description"]
    assert body["url"] == LINK and body["file_url"] is None


def test_admin_creates_resource_with_uploaded_file(as_admin_ia: TestClient, ia: Academy) -> None:
    files = {"file": ("d.png", _png(), "image/png")}
    response = _create(as_admin_ia, ia.id, files=files, type="document", title="Diagrama")
    assert response.status_code == 201
    body = response.json()
    assert body["url"] is None
    assert body["file_url"].startswith("/media/resource/")
    assert as_admin_ia.get(body["file_url"]).status_code == 200


def test_create_requires_url_or_file_422(as_admin_ia: TestClient, ia: Academy) -> None:
    for data in ({"type": "link", "title": "x"}, {"type": "link", "title": "x", "url": ""}):
        response = _create(as_admin_ia, ia.id, **data)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "url_or_file_required"


@pytest.mark.parametrize("url", ["javascript:alert(1)", "ftp://example.com/x", "not a url"])
def test_create_rejects_non_http_url_422(as_admin_ia: TestClient, ia: Academy, url: str) -> None:
    response = _create(as_admin_ia, ia.id, type="link", title="x", url=url)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_create_rejects_bad_type_and_empty_title_422(as_admin_ia: TestClient, ia: Academy) -> None:
    assert _create(as_admin_ia, ia.id, type="pdf", title="x", url=LINK).status_code == 422
    assert _create(as_admin_ia, ia.id, type="link", title="", url=LINK).status_code == 422


def test_create_rejects_non_image_file_422(as_admin_ia: TestClient, ia: Academy, db: Session) -> None:
    files = {"file": ("a.pdf", b"%PDF-1.4 fake", "application/pdf")}
    assert _create(as_admin_ia, ia.id, files=files, type="document", title="x").status_code == 422
    assert db.scalar(select(Resource).where(Resource.title == "x")) is None


def test_admin_patches_resource(as_admin_ia: TestClient, ia: Academy, db: Session) -> None:
    resource = _add(db, ia)
    response = as_admin_ia.patch(
        f"/api/resources/{resource.id}", json={"title": "Nuevo", "type": "video", "description": "**ok**"}
    )
    assert response.status_code == 200
    body = response.json()
    assert (body["title"], body["type"], body["description"]) == ("Nuevo", "video", "**ok**")
    assert body["url"] == LINK


def test_patch_rejects_unknown_fields_422(as_admin_ia: TestClient, ia: Academy, db: Session) -> None:
    resource = _add(db, ia)
    assert as_admin_ia.patch(f"/api/resources/{resource.id}", json={"academy_id": 999}).status_code == 422
    assert db.get(Resource, resource.id).academy_id == ia.id


def test_patch_cannot_clear_url_without_file_422(as_admin_ia: TestClient, ia: Academy, db: Session) -> None:
    resource = _add(db, ia)
    response = as_admin_ia.patch(f"/api/resources/{resource.id}", json={"url": None})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "url_or_file_required"


def test_patch_can_clear_url_when_file_exists(as_admin_ia: TestClient, ia: Academy, db: Session) -> None:
    resource = _add(db, ia)
    assert _upload(as_admin_ia, resource.id).status_code == 200
    response = as_admin_ia.patch(f"/api/resources/{resource.id}", json={"url": None})
    assert response.status_code == 200
    assert response.json()["url"] is None and response.json()["file_url"]


def test_upload_replaces_previous_file(as_admin_ia: TestClient, ia: Academy, db: Session) -> None:
    resource = _add(db, ia)
    first = _upload(as_admin_ia, resource.id).json()["file_url"]
    second = _upload(as_admin_ia, resource.id).json()["file_url"]
    assert first != second
    assert as_admin_ia.get(first).status_code == 404
    assert as_admin_ia.get(second).status_code == 200


def test_upload_keeps_previous_file_when_commit_fails(
    as_admin_ia: TestClient, ia: Academy, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    resource = _add(db, ia)
    first = _upload(as_admin_ia, resource.id).json()["file_url"]

    def boom() -> None:
        raise RuntimeError("db down")

    monkeypatch.setattr(db, "commit", boom)
    assert _upload(as_admin_ia, resource.id).status_code == 500
    monkeypatch.undo()
    assert db.get(Resource, resource.id).file_url == first
    assert as_admin_ia.get(first).status_code == 200


def test_admin_deletes_resource_and_its_file(as_admin_ia: TestClient, ia: Academy, db: Session) -> None:
    resource = _add(db, ia)
    file_url = _upload(as_admin_ia, resource.id).json()["file_url"]
    assert as_admin_ia.delete(f"/api/resources/{resource.id}").status_code == 204
    assert db.scalar(select(Resource).where(Resource.id == resource.id)) is None
    assert as_admin_ia.get(file_url).status_code == 404


def test_missing_resource_404(as_superadmin: TestClient) -> None:
    assert as_superadmin.patch("/api/resources/9999", json={"title": "x"}).status_code == 404
    assert as_superadmin.delete("/api/resources/9999").status_code == 404
