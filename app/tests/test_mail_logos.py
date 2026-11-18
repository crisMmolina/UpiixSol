"""Email logos and covers (UPS-098): WebP/PNG get the email copy, SVG never falls back to the old wordmark."""

import io
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from app.models import Academy, Event
from app.models.site import SiteSettings
from app.services import mail_campaigns, mail_images
from app.services.media import save_image_bytes
from app.services.site import DEFAULTS

SVG = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><circle cx="5" cy="5" r="4"/></svg>'
OLD_WORDMARK = "/brand/upiixsol/wordmark.png"
PREVIEW = "/api/mail/preview"


def _png(size=(300, 120), color=(185, 45, 93, 255)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGBA", size, color).save(buffer, "PNG")
    return buffer.getvalue()


def _set_site_logo(db: Session, url: str) -> None:
    row = db.get(SiteSettings, 1) or SiteSettings(id=1, **DEFAULTS)
    row.logo_url = url
    db.add(row)
    db.commit()


def _club(db: Session, logo_url: str | None) -> Academy:
    club = db.query(Academy).filter_by(is_active=True).first()
    assert club is not None
    club.logo_url = logo_url
    db.commit()
    return club


def _preview(client: TestClient, blocks: list[dict] | None = None, **extra: object) -> str:
    payload = {
        "subject": "Aviso",
        "blocks": blocks or [{"kind": "paragraph", "text": "Hola"}],
        "audience": {"kind": "individual", "emails": ["a@ipn.mx"]},
    } | extra
    response = client.post(PREVIEW, json=payload)
    assert response.status_code == 200, response.text
    return response.json()["html"]


def _renderer_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """UPS-099 rasterizes SVG logos; the text wordmark is what an SVG that cannot be rendered gets."""

    def boom(*_args, **_kwargs):
        raise ValueError("render failed")

    monkeypatch.setattr(mail_images.resvg_py, "svg_to_bytes", boom)


def test_svg_site_logo_never_uses_the_outdated_bundled_wordmark(
    as_superadmin: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _renderer_fails(monkeypatch)
    _set_site_logo(db, save_image_bytes(SVG, "logo"))
    html = _preview(as_superadmin)
    assert OLD_WORDMARK not in html and ".svg" not in html
    assert ">UpiixSol</span>" in html  # the text wordmark


def test_webp_site_logo_uses_email_copy(as_superadmin: TestClient, db: Session) -> None:
    webp = save_image_bytes(_png(), "logo")
    assert webp.endswith(".webp")
    _set_site_logo(db, webp)
    html = _preview(as_superadmin)
    assert "/media/mail/" in html and ".webp" not in html


def test_png_site_logo_uploaded_in_marca_del_sitio_shows_in_email(
    as_superadmin: TestClient, db: Session
) -> None:
    # What Marca del sitio stores for an uploaded PNG: the WebP of the logo pipeline.
    _set_site_logo(db, save_image_bytes(_png(), "logo"))
    html = _preview(as_superadmin)
    assert '<img src="' in html and "/media/mail/" in html and OLD_WORDMARK not in html
    assert 'alt="UpiixSol"' in html


def test_svg_club_logo_falls_back_to_club_name(
    as_superadmin: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _renderer_fails(monkeypatch)
    club = _club(db, save_image_bytes(SVG, "logo"))
    html = _preview(as_superadmin, sender_academy_id=club.id)
    assert f">{club.name}</span>" in html and ".svg" not in html


def test_webp_event_cover_uses_email_copy(as_superadmin: TestClient, db: Session) -> None:
    cover = save_image_bytes(_png((800, 400)), "cover")
    assert cover.endswith(".webp")
    event = Event(
        title="Taller",
        starts_at=datetime(2026, 12, 2, 20, tzinfo=UTC),
        ends_at=datetime(2026, 12, 2, 22, tzinfo=UTC),
        cover_url=cover,
    )
    db.add(event)
    db.commit()
    html = _preview(as_superadmin, blocks=[{"kind": "event", "event_id": event.id}])
    assert "/media/mail/" in html and cover.rsplit("/", 1)[1] not in html


def test_preview_and_send_use_the_same_logo(db: Session, seeded: dict) -> None:
    _set_site_logo(db, save_image_bytes(_png(), "logo"))
    club = _club(db, save_image_bytes(_png(), "logo"))
    first = mail_campaigns.email_identity(db, club)
    assert first[1].site_logo_url and first[1].site_logo_url.startswith("/media/mail/")
    assert first[0].logo_url and first[0].logo_url.startswith("/media/mail/")
    assert mail_campaigns.email_identity(db, club) == first  # cached copy: same URL every time
