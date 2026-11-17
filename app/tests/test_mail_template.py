"""Campus email template (UPS-075, spec 003 §Composing and sending): escaping, links, brand, footer."""

import re
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import get_settings
from app.main import app
from app.models.site import SiteSettings
from app.services import mail_template
from app.services.mailer import BatchResult, MailMessage, MailRecipientVars, get_mail_transport
from app.services.site import get_site


class FakeTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[MailMessage, list[MailRecipientVars]]] = []

    def send_batch(self, message: MailMessage, recipients: list[MailRecipientVars]) -> BatchResult:
        self.calls.append((message, list(recipients)))
        return BatchResult(accepted={r.recipient_id: f"fake-{r.recipient_id}" for r in recipients})


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeTransport]:
    monkeypatch.setattr(get_settings(), "mail_enabled", True)
    transport = FakeTransport()
    app.dependency_overrides[get_mail_transport] = lambda: transport
    yield transport
    app.dependency_overrides.pop(get_mail_transport, None)


def test_body_html_is_escaped_and_urls_become_links() -> None:
    body = (
        "<b>Hola</b> & bienvenidos: https://upiixsol.com/a?b=1&c=2.\n"
        "segunda línea\n\n"
        "javascript:alert(1) y <script>x</script>"
    )
    html, text = mail_template.render("Aviso", body, "Recibes este correo porque eres parte de UpiixSol.")
    assert "&lt;b&gt;Hola&lt;/b&gt; &amp; bienvenidos" in html
    assert '<a href="https://upiixsol.com/a?b=1&amp;c=2"' in html
    assert "c=2</a>." in html  # the final period is not part of the link
    assert "segunda línea" in html and "<br>" in html
    assert len(re.findall(r"<p\b", html)) >= 2  # a blank line starts a new paragraph
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert 'href="javascript' not in html
    assert body in text  # the plain-text part is the text as typed


def test_subject_with_newline_is_422(as_superadmin: TestClient, fake: FakeTransport) -> None:
    for path, extra in (("/api/mail/test", {}), ("/api/mail/campaigns", {"audience": {"kind": "all"}})):
        response = as_superadmin.post(path, json={"subject": "Hola\nBcc: x@ipn.mx", "body": "Texto", **extra})
        assert response.status_code == 422, response.text
    too_long = as_superadmin.post("/api/mail/test", json={"subject": "a" * 151, "body": "Texto"})
    assert too_long.status_code == 422
    empty_body = as_superadmin.post("/api/mail/test", json={"subject": "Hola", "body": " "})
    assert empty_body.status_code == 422
    assert fake.calls == []


def test_template_uses_site_brand_and_public_base_url(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "public_base_url", "https://campus.test/")
    db.add(
        SiteSettings(
            id=1,
            name="ClubSol",
            logo_url="/media/site/logo.webp",
            color_primary="#00BF63",
            color_secondary="#04944F",
            color_accent="#F28034",
        )
    )
    db.flush()
    html, text = mail_template.render("Aviso", "Hola", "Motivo.", site=get_site(db))
    assert "ClubSol" in html
    assert 'src="https://campus.test/media/site/logo.webp"' in html
    assert 'href="https://campus.test"' in html
    assert "ClubSol" in text


def test_footer_says_why_you_got_it() -> None:
    reason = mail_template.footer_reason
    assert reason("all", site_name="UpiixSol") == "Recibes este correo porque eres parte de UpiixSol."
    assert reason("role", site_name="UpiixSol") == "Recibes este correo porque eres parte de UpiixSol."
    assert (
        reason("academy", site_name="UpiixSol", club_name="Robótica")
        == "Recibes este correo porque eres parte de Robótica."
    )
    assert (
        reason("individual", site_name="UpiixSol", sender_nickname="ana")
        == "Recibes este correo porque ana te lo envió."
    )
    html, text = mail_template.render("Aviso", "Hola", "Recibes este correo porque ana te lo envió.")
    assert "Recibes este correo porque ana te lo envió." in html
    assert f'href="{mail_template.UNSUBSCRIBE_HREF}"' in html and "Darte de baja" in html
    assert mail_template.UNSUBSCRIBE_HREF in text


def test_absolute_logo_and_url_without_host_stay_safe(db: Session) -> None:
    site = get_site(db).model_copy(update={"logo_url": "https://cdn.test/logo.png"})
    html, _text = mail_template.render("Aviso", "Mira http://. y sigue", "Motivo.", site=site)
    assert 'src="https://cdn.test/logo.png"' in html
    assert 'href="http://"' not in html and "Mira http://. y sigue" in html
    no_logo, _ = mail_template.render(
        "Aviso", "Hola", "Motivo.", site=site.model_copy(update={"logo_url": None})
    )
    assert "<img" not in no_logo and site.name in no_logo
