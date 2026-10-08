"""MEDIA_STORAGE=database (UPS-030): uploads live in media_objects and /media serves them from there."""

import io
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.db import get_db
from app.main import MEDIA_CSP, create_app
from app.models import MediaObject
from app.services import media
from app.services.media import StorageSettings, delete_media, save_image_bytes

SVG = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><circle cx="5" cy="5" r="4"/></svg>'


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (40, 20), (0, 191, 99)).save(buffer, "PNG")
    return buffer.getvalue()


@pytest.fixture
def in_database(engine: Engine, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(media, "media_storage", lambda: "database")
    monkeypatch.setattr(media, "SessionLocal", sessionmaker(bind=engine, expire_on_commit=False))


@pytest.fixture
def site(db: Session, in_database: None, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setattr("app.main.media_storage", lambda: "database")
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        yield client


def test_uploads_are_stored_in_the_database(db: Session, in_database: None) -> None:
    url = save_image_bytes(_png(), "post")
    logo = save_image_bytes(SVG, "logo")
    assert url.startswith("/media/post/") and url.endswith(".webp")
    stored = {row.key: row for row in db.scalars(select(MediaObject))}
    assert stored[url.removeprefix("/media/")].content_type == "image/webp"
    assert stored[logo.removeprefix("/media/")].content_type == "image/svg+xml"
    assert stored[logo.removeprefix("/media/")].data == SVG


def test_media_is_served_from_the_database_with_its_csp(site: TestClient) -> None:
    url = save_image_bytes(_png(), "avatar")
    response = site.get(url)
    assert response.status_code == 200 and response.headers["content-type"] == "image/webp"
    assert response.headers["content-security-policy"] == MEDIA_CSP
    assert "immutable" in response.headers["cache-control"]
    with Image.open(io.BytesIO(response.content)) as image:
        assert image.format == "WEBP"


UNKNOWN = "/media/post/" + "0" * 32 + ".webp"


@pytest.mark.parametrize("path", [UNKNOWN, "/media/post/x.webp", "/media/post/" + "a" * 32 + ".png"])
def test_unknown_or_malformed_media_is_404(site: TestClient, path: str) -> None:
    assert site.get(path).status_code == 404


def test_delete_media_removes_the_row_and_ignores_foreign_keys(db: Session, in_database: None) -> None:
    url = save_image_bytes(_png(), "cover")
    delete_media("/media/cover/../../users")  # malformed: never reaches a query
    delete_media("https://example.com/foto.webp")  # foreign URL
    assert db.scalar(select(MediaObject.key)) == url.removeprefix("/media/")
    delete_media(url)
    db.expire_all()
    assert db.scalar(select(MediaObject.key)) is None


def test_storage_defaults_to_disk_and_reads_media_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MEDIA_STORAGE", raising=False)
    assert StorageSettings(_env_file=None).media_storage == "disk"
    assert media.media_storage() in ("disk", "database")
    monkeypatch.setenv("MEDIA_STORAGE", "database")
    assert StorageSettings(_env_file=None).media_storage == "database"
