"""Backend pieces of the web composer (UPS-091): image click-through link and the default Reply-To."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import get_settings
from app.services.mail_blocks import Blocks
from app.tests.test_mail_render import _render

IMAGE = {"kind": "image", "url": "https://www.upiixsol.com/media/mail/a.png", "alt": "Cartel"}


def test_image_link_wraps_the_image_in_an_anchor() -> None:
    html, text = _render({**IMAGE, "link": "https://www.upiixsol.com/a/ia"})
    assert '<a href="https://www.upiixsol.com/a/ia"' in html
    assert "https://www.upiixsol.com/a/ia" in text


def test_image_without_link_is_not_clickable() -> None:
    html, _ = _render(IMAGE)
    assert 'alt="Cartel"' in html and 'href="https://www.upiixsol.com/media' not in html


def test_blank_image_link_is_ignored_and_a_bad_one_is_refused() -> None:
    assert Blocks.model_validate([{**IMAGE, "link": "  "}]).root[0].link is None
    with pytest.raises(ValidationError):
        Blocks.model_validate([{**IMAGE, "link": "javascript:alert(1)"}])


def test_default_reply_to_comes_from_settings(
    as_admin_ia: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "mail_reply_to", "")
    assert as_admin_ia.get("/api/mail/reply-to").json() == {"reply_to": None}
    monkeypatch.setattr(get_settings(), "mail_reply_to", "mesa@upiixsol.com")
    assert as_admin_ia.get("/api/mail/reply-to").json() == {"reply_to": "mesa@upiixsol.com"}
