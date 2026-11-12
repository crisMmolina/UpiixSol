"""Site brand (UPS-041): public read with defaults, superadmin-only writes, logo/mascot upload and removal."""

import io
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.models import MediaObject, SiteSettings
from app.services import media
from app.services.site import DEFAULTS

SVG = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><circle cx="5" cy="5" r="4"/></svg>'
EVIL_SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
VALID = {
    "name": "UpiixLuna",
    "color_primary": "#1e40af",
    "color_secondary": "#B91C1C",
    "color_accent": "#CA8A04",
}


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGBA", (64, 32), (0, 191, 99, 255)).save(buffer, "PNG")
    return buffer.getvalue()


def _on_disk(url: str) -> Path:
    return Path(get_settings().media_dir) / url.removeprefix("/media/")


def _upload(client: TestClient, kind: str, data: bytes | None = None, name: str = "x.png"):
    return client.post(f"/api/admin/site/{kind}", files={"file": (name, data or _png(), "image/png")})


# ── Public read ──────────────────────────────────────────────


def test_public_read_returns_the_defaults_without_a_row(client: TestClient) -> None:
    response = client.get("/api/site")
    assert response.status_code == 200
    assert response.json() == DEFAULTS
    assert response.headers["cache-control"] == "public, max-age=60"


def test_public_read_returns_the_stored_brand(client: TestClient, db: Session) -> None:
    db.add(SiteSettings(id=1, **{**DEFAULTS, "name": "UpiixMar", "logo_url": None}))
    db.flush()
    body = client.get("/api/site").json()
    assert body["name"] == "UpiixMar" and body["logo_url"] is None
    assert body["mascot_url"] == DEFAULTS["mascot_url"]


# ── Writes: superadmin only ──────────────────────────────────


WRITES = [
    ("PUT", "/api/admin/site", {"json": VALID}),
    ("POST", "/api/admin/site/logo", {"files": {"file": ("x.png", b"png", "image/png")}}),
    ("POST", "/api/admin/site/mascot", {"files": {"file": ("x.png", b"png", "image/png")}}),
    ("DELETE", "/api/admin/site/logo", {}),
    ("DELETE", "/api/admin/site/mascot", {}),
]


@pytest.mark.parametrize(("method", "path", "kwargs"), WRITES, ids=lambda v: v if isinstance(v, str) else "")
def test_writes_need_a_superadmin(
    method: str, path: str, kwargs: dict, client: TestClient, as_admin_ia: TestClient, as_member: TestClient
) -> None:
    assert client.request(method, path, **kwargs).status_code == 401
    assert as_member.request(method, path, **kwargs).status_code == 403
    assert as_admin_ia.request(method, path, **kwargs).status_code == 403
    assert client.get("/api/site").json() == DEFAULTS  # nothing changed


def test_superadmin_updates_name_and_colors(as_superadmin: TestClient, db: Session) -> None:
    response = as_superadmin.put("/api/admin/site", json={**VALID, "name": "  UpiixLuna  "})
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "UpiixLuna"
    assert body["color_primary"] == "#1E40AF"  # normalized to upper case
    assert body["logo_url"] == DEFAULTS["logo_url"] and body["mascot_url"] == DEFAULTS["mascot_url"]
    assert as_superadmin.get("/api/site").json() == body
    assert db.get(SiteSettings, 1).name == "UpiixLuna"


@pytest.mark.parametrize(
    "change",
    [
        {"name": "U"},
        {"name": "x" * 41},
        {"name": "Upiix\nSol"},
        {"name": "Upiix\u202eloS"},  # right-to-left override
        {"name": "Upiix\u2066Sol\u2069"},  # isolates
        {"name": "Upiix\u200fSol"},  # right-to-left mark
        {"name": "   "},
        {"color_primary": "green"},
        {"color_secondary": "#12345"},
        {"color_accent": "#GGGGGG"},
        {"logo_url": "https://evil.example/logo.png"},  # images only through the upload endpoints
    ],
)
def test_invalid_brand_is_422(as_superadmin: TestClient, change: dict) -> None:
    response = as_superadmin.put("/api/admin/site", json={**VALID, **change})
    assert response.status_code == 422
    assert as_superadmin.get("/api/site").json() == DEFAULTS


def test_name_limits_are_inclusive(as_superadmin: TestClient) -> None:
    assert as_superadmin.put("/api/admin/site", json={**VALID, "name": "Up"}).status_code == 200
    assert as_superadmin.put("/api/admin/site", json={**VALID, "name": "U" * 40}).status_code == 200


# ── Logo and mascot (disk storage) ───────────────────────────


@pytest.mark.parametrize("kind", ["logo", "mascot"])
def test_upload_replace_and_remove(as_superadmin: TestClient, kind: str) -> None:
    first = _upload(as_superadmin, kind)
    assert first.status_code == 200
    first_url = first.json()[f"{kind}_url"]
    assert first_url.startswith(f"/media/{kind}/") and first_url.endswith(".webp")
    assert _on_disk(first_url).is_file()
    assert as_superadmin.get("/api/site").json()[f"{kind}_url"] == first_url

    second = _upload(as_superadmin, kind, SVG, "x.svg").json()[f"{kind}_url"]
    assert second.endswith(".svg") and _on_disk(second).read_bytes() == SVG
    assert not _on_disk(first_url).exists()  # the replaced upload is cleaned up

    removed = as_superadmin.delete(f"/api/admin/site/{kind}")
    assert removed.status_code == 200 and removed.json()[f"{kind}_url"] is None
    assert not _on_disk(second).exists()
    assert as_superadmin.get("/api/site").json()[f"{kind}_url"] is None
    # Removing again is a no-op, and the other image is untouched.
    other = "mascot" if kind == "logo" else "logo"
    again = as_superadmin.delete(f"/api/admin/site/{kind}").json()
    assert again[f"{kind}_url"] is None and again[f"{other}_url"] == DEFAULTS[f"{other}_url"]


def test_removing_the_built_in_logo_keeps_its_file(as_superadmin: TestClient) -> None:
    removed = as_superadmin.delete("/api/admin/site/logo").json()
    assert removed["logo_url"] is None and removed["name"] == DEFAULTS["name"]
    web_logo = Path(__file__).resolve().parents[2] / "web" / "public" / "brand" / "upiixsol" / "wordmark.png"
    assert web_logo.is_file()


@pytest.mark.parametrize(
    ("data", "status"),
    [(b"not an image", 422), (EVIL_SVG, 422), (b"", 422), (b"\x89PNG" + b"0" * (2 * 1024 * 1024), 413)],
)
def test_bad_uploads_keep_the_current_image(as_superadmin: TestClient, data: bytes, status: int) -> None:
    response = as_superadmin.post("/api/admin/site/logo", files={"file": ("x.svg", data, "image/svg+xml")})
    assert response.status_code == status
    assert as_superadmin.get("/api/site").json()["logo_url"] == DEFAULTS["logo_url"]


def test_failed_commit_keeps_the_previous_logo(
    as_superadmin: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = _upload(as_superadmin, "logo").json()["logo_url"]
    before = {p.name for p in _on_disk(first).parent.iterdir()}

    def boom() -> None:
        raise RuntimeError("db down")

    monkeypatch.setattr(db, "commit", boom)
    assert _upload(as_superadmin, "logo").status_code == 500
    assert {p.name for p in _on_disk(first).parent.iterdir()} == before  # new file removed, previous kept
    assert _on_disk(first).is_file()


def test_simultaneous_uploads_never_orphan_a_file(
    as_superadmin: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Upload B read the row before upload A committed: B must replace (and delete) A, not the stale value."""
    from app.services import site as service

    first = _upload(as_superadmin, "logo").json()["logo_url"]
    real = service._stored
    reads: list[str | None] = []

    def stale_once(db: Session, field: str) -> str | None:
        reads.append(field)
        return DEFAULTS["logo_url"] if len(reads) == 1 else real(db, field)

    monkeypatch.setattr(service, "_stored", stale_once)
    second = _upload(as_superadmin, "logo").json()["logo_url"]
    assert len(reads) == 2  # the stale swap did not apply; the retry read the committed value
    assert not _on_disk(first).exists() and _on_disk(second).is_file()
    assert as_superadmin.get("/api/site").json()["logo_url"] == second


def test_a_brand_that_keeps_changing_is_a_conflict(
    as_superadmin: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services import site as service

    first = _upload(as_superadmin, "logo").json()["logo_url"]
    before = {p.name for p in _on_disk(first).parent.iterdir()}
    monkeypatch.setattr(service, "_stored", lambda _db, _field: "/media/logo/stale.webp")
    response = _upload(as_superadmin, "logo")
    assert response.status_code == 409
    assert {p.name for p in _on_disk(first).parent.iterdir()} == before  # the new file was removed
    assert as_superadmin.delete("/api/admin/site/logo").status_code == 409
    monkeypatch.undo()
    assert as_superadmin.get("/api/site").json()["logo_url"] == first


# ── MEDIA_STORAGE=database ───────────────────────────────────


@pytest.fixture
def in_database(engine: Engine, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(media, "media_storage", lambda: "database")
    monkeypatch.setattr(media, "SessionLocal", sessionmaker(bind=engine, expire_on_commit=False))
    yield


def _keys(db: Session) -> set[str]:
    db.expire_all()
    return set(db.scalars(select(MediaObject.key)))


@pytest.mark.parametrize("kind", ["logo", "mascot"])
def test_database_storage_upload_replace_and_remove(
    as_superadmin: TestClient, db: Session, in_database: None, kind: str
) -> None:
    first = _upload(as_superadmin, kind).json()[f"{kind}_url"]
    assert _keys(db) == {first.removeprefix("/media/")}
    assert not _on_disk(first).exists()

    second = _upload(as_superadmin, kind, SVG, "x.svg").json()[f"{kind}_url"]
    assert _keys(db) == {second.removeprefix("/media/")}  # the replaced row is gone

    assert as_superadmin.delete(f"/api/admin/site/{kind}").json()[f"{kind}_url"] is None
    assert _keys(db) == set()
