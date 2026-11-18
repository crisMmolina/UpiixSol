"""Email images (UPS-088): upload endpoint, PNG/JPEG copies under /media/mail, logo/cover copies."""

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import get_settings
from app.main import app
from app.services import mail_images
from app.services.media import save_image_bytes

SVG = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><circle cx="5" cy="5" r="4"/></svg>'


def _image(fmt: str, size=(300, 200), mode="RGB", color=(0, 191, 99)) -> bytes:
    buffer = io.BytesIO()
    Image.new(mode, size, color).save(buffer, fmt)
    return buffer.getvalue()


def _upload(client: TestClient, data: bytes, name: str = "x.png", content_type: str = "image/png"):
    return client.post("/api/mail/images", files={"file": (name, data, content_type)})


def _stored(url: str) -> Path:
    assert url.startswith(get_settings().public_base_url.rstrip("/") + "/media/mail/")
    return Path(get_settings().media_dir) / "mail" / url.rsplit("/", 1)[1]


def _format(url: str) -> tuple[str | None, tuple[int, int]]:
    with Image.open(_stored(url)) as image:
        return image.format, image.size


@pytest.mark.parametrize(
    ("fmt", "mode", "color", "expected", "ext"),
    [
        ("PNG", "RGB", (0, 191, 99), "JPEG", ".jpg"),
        ("JPEG", "RGB", (10, 20, 30), "JPEG", ".jpg"),
        ("WEBP", "RGB", (1, 2, 3), "JPEG", ".jpg"),
        ("PNG", "RGBA", (0, 191, 99, 0), "PNG", ".png"),  # transparency stays transparent
        ("WEBP", "RGBA", (0, 191, 99, 0), "PNG", ".png"),
    ],
)
def test_upload_png_jpg_webp_stores_jpeg_or_png_copy(
    as_superadmin: TestClient, fmt: str, mode: str, color: tuple, expected: str, ext: str
) -> None:
    response = _upload(as_superadmin, _image(fmt, mode=mode, color=color))
    assert response.status_code == 201
    url = response.json()["url"]
    assert url.endswith(ext)
    assert _format(url)[0] == expected


def test_svg_is_refused(as_superadmin: TestClient) -> None:
    response = _upload(as_superadmin, SVG, "logo.svg", "image/svg+xml")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_image"
    assert _upload(as_superadmin, b"not an image").status_code == 422


def test_email_image_too_large_is_413(as_superadmin: TestClient) -> None:
    response = _upload(as_superadmin, b"\x00" * (5 * 1024 * 1024 + 1))
    assert response.status_code == 413


def test_resized_to_1200_wide(as_superadmin: TestClient) -> None:
    url = _upload(as_superadmin, _image("PNG", size=(2400, 600))).json()["url"]
    assert _format(url)[1] == (1200, 300)
    small = _upload(as_superadmin, _image("PNG", size=(400, 300))).json()["url"]
    assert _format(small)[1] == (400, 300)  # never enlarged


def test_mail_media_is_public_without_session(as_admin_ia: TestClient) -> None:
    url = _upload(as_admin_ia, _image("PNG")).json()["url"]
    with TestClient(app) as anon:
        response = anon.get("/media/mail/" + url.rsplit("/", 1)[1])
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"


def test_email_copy_of_site_logo_and_event_cover(seeded: dict) -> None:
    logo = save_image_bytes(_image("PNG", mode="RGBA", color=(0, 191, 99, 0)), "logo")
    cover = save_image_bytes(_image("PNG", size=(1600, 800)), "cover")
    assert logo.endswith(".webp") and cover.endswith(".webp")
    logo_copy = mail_images.email_copy(logo)
    cover_copy = mail_images.email_copy(cover)
    assert logo_copy and logo_copy.startswith("/media/mail/") and logo_copy.endswith(".png")
    assert cover_copy and cover_copy.startswith("/media/mail/") and cover_copy.endswith(".jpg")
    assert mail_images.email_copy(logo) == logo_copy  # cached: same copy, no new file
    assert mail_images.email_copy(cover) == cover_copy
    # Already PNG/JPEG (e.g. the static wordmark) and absolute URLs of ours pass through unchanged.
    assert mail_images.email_copy("/brand/upiixsol/wordmark.png") == "/brand/upiixsol/wordmark.png"
    assert mail_images.email_copy(None) is None
    assert mail_images.email_copy("/media/cover/" + "0" * 32 + ".webp") is None  # missing source


def test_svg_club_logo_falls_back_to_site_logo_or_wordmark(seeded: dict) -> None:
    svg = save_image_bytes(SVG, "logo")
    assert mail_images.email_copy(svg) is None  # no new dependency to rasterize it
    site = save_image_bytes(_image("PNG", mode="RGBA", color=(0, 191, 99, 0)), "logo")
    site_copy = mail_images.email_copy(site)
    assert site_copy
    assert mail_images.email_logo(svg, site) == site_copy  # club SVG → site logo
    assert mail_images.email_logo(svg, svg) is None  # → the renderer shows the wordmark
    assert mail_images.email_logo(None, None) is None


def test_member_and_anon_cannot_upload(as_member: TestClient) -> None:
    assert _upload(as_member, _image("PNG")).status_code == 403
    with TestClient(app) as anon:
        assert _upload(anon, _image("PNG")).status_code == 401


def test_email_copy_edge_cases(seeded: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    base = get_settings().public_base_url.rstrip("/")
    cover = save_image_bytes(_image("PNG", size=(800, 400)), "cover")
    assert mail_images.email_copy(base + cover) == mail_images.email_copy(cover)  # absolute URL of ours
    assert mail_images.email_copy("https://evil.example" + cover) is None  # foreign host
    assert mail_images.email_copy("https://cdn.example/logo.png") == "https://cdn.example/logo.png"
    assert mail_images.email_copy("/brand/x.webp") is None  # not a stored upload
    corrupt = Path(get_settings().media_dir) / "cover" / ("a" * 32 + ".webp")
    corrupt.write_bytes(b"not webp")
    assert mail_images.email_copy("/media/cover/" + "a" * 32 + ".webp") is None


def test_email_copy_in_database_storage(db, engine, monkeypatch: pytest.MonkeyPatch) -> None:
    from sqlalchemy.orm import sessionmaker

    from app.services import media

    monkeypatch.setattr(media, "media_storage", lambda: "database")
    monkeypatch.setattr(media, "SessionLocal", sessionmaker(bind=engine, expire_on_commit=False))
    cover = save_image_bytes(_image("PNG", size=(800, 400)), "cover")
    copy = mail_images.email_copy(cover)
    assert copy and copy.startswith("/media/mail/") and copy.endswith(".jpg")
    assert mail_images.email_copy(cover) == copy
    assert media.read_public("mail/" + "0" * 32 + ".jpg") is None
    assert media.read_public("bad key") is None
