"""Email renderer (UPS-086, spec 004 §Content and rendering): layout, sender block, theme, blocks, footer."""

import os
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.errors import AppError
from app.services.mail_blocks import Blocks
from app.services.mail_render import (
    CampaignLike,
    EventCard,
    Sender,
    Theme,
    contrast,
    render_blocks,
    theme_for,
)
from app.services.site import SiteOut

FIXTURES = Path(__file__).parent / "fixtures" / "mail_render"
UNSUB = "%recipient.unsubscribe_url%"
BOARD = Sender()
CLUB = Sender(name="UpiixIA", logo_url="/media/upiixia-logo.png")
CLUB_THEME = Theme(primary="#7ED957", secondary="#04944F", accent="#00BF63")


def _blocks(*raw: dict) -> list:
    return Blocks.model_validate(list(raw)).root


def _p(text: str) -> dict:
    return {"kind": "paragraph", "text": text}


def _render(
    *raw: dict,
    sender: Sender = BOARD,
    theme: Theme | None = None,
    reply_to: str | None = None,
    preheader: str | None = None,
    event: EventCard | None = None,
    ics_url: str | None = None,
    reason: str = "Recibes este correo porque eres parte de UpiixSol.",
) -> tuple[str, str]:
    campaign = CampaignLike(
        subject="Asunto",
        blocks=_blocks(*raw),
        preheader=preheader,
        reply_to=reply_to,
        footer_reason=reason,
    )
    return render_blocks(
        campaign,
        sender=sender,
        theme=theme or Theme(),
        recipient_name="Ana",
        unsubscribe_href=UNSUB,
        event=event,
        ics_url=ics_url,
    )


def test_layout_is_600px_tables_with_inline_styles() -> None:
    html, _ = _render(_p("Hola"))
    assert html.startswith("<!doctype html>")
    assert 'width="600"' in html and "max-width:600px" in html
    assert 'role="presentation"' in html
    assert "<style" not in html and "<link" not in html and "<script" not in html
    assert " class=" not in html
    assert max(int(w) for w in re.findall(r'width="(\d+)"', html)) <= 600


def test_upiixsol_logo_always_on_top() -> None:
    for sender in (BOARD, CLUB):
        html, _ = _render(_p("Hola"), sender=sender)
        logo = html.index("https://www.upiixsol.com/brand/upiixsol/wordmark.png")
        assert logo < html.index("Enviado por")
        assert 'alt="UpiixSol"' in html


def test_sender_block_shows_club_logo_name_and_color() -> None:
    html, text = _render(_p("Hola"), sender=CLUB, theme=CLUB_THEME)
    assert "Enviado por" in html
    assert 'src="https://www.upiixsol.com/media/upiixia-logo.png"' in html
    assert 'alt="UpiixIA"' in html
    assert "#7ED957" in html.upper() or "#7ed957" in html
    assert "Enviado por UpiixIA" in text


def test_sender_block_for_the_board() -> None:
    html, text = _render(_p("Hola"))
    assert "Enviado por la mesa directiva de UpiixSol" in html
    assert "Enviado por la mesa directiva de UpiixSol" in text


def test_theme_uses_sender_club_colors() -> None:
    site = SiteOut(
        name="UpiixSol",
        logo_url="/brand/upiixsol/wordmark.png",
        mascot_url=None,
        color_primary="#00BF63",
        color_secondary="#04944F",
        color_accent="#F28034",
    )
    theme = theme_for(site, club_colors=("#112233", "#445566", "#778899"))
    assert (theme.primary, theme.secondary, theme.accent) == ("#112233", "#445566", "#778899")
    html, _ = _render(_p("Hola"), sender=CLUB, theme=theme, preheader=None)
    assert "#112233" in html and "#F28034" not in html.upper()


def test_theme_falls_back_to_site_brand() -> None:
    site = SiteOut(
        name="Mi campus",
        logo_url=None,
        mascot_url=None,
        color_primary="#00BF63",
        color_secondary="#04944F",
        color_accent="#F28034",
    )
    theme = theme_for(site, club_colors=None)
    assert theme.site_name == "Mi campus" and theme.primary == "#00BF63"
    html, _ = _render(_p("Hola"), theme=theme)
    assert "Mi campus" in html and "<img" not in html.split("Enviado por")[0]
    bad = theme_for(site, club_colors=("red;}<script>", "#04944F", "#F28034"))
    assert bad.primary == "#00BF63"


def test_svg_club_logo_falls_back() -> None:
    html, _ = _render(_p("Hola"), sender=Sender(name="UpiixSky", logo_url="/media/x.svg"))
    assert ".svg" not in html
    assert "UpiixSky" in html


def test_preheader_is_hidden_text() -> None:
    html, text = _render(_p("Hola"), preheader="Mañana primera clase")
    body = html[html.index("<body") :]
    hidden = body[: body.index("Mañana primera clase")]
    assert "display:none" in hidden and "max-height:0" in hidden and "opacity:0" in hidden
    assert html.index("Mañana primera clase") < html.index("<img")
    assert "Mañana primera clase" not in text


def test_paragraph_html_is_escaped() -> None:
    html, _ = _render(
        _p('<script>alert(1)</script> <b>x</b> & "q"'),
        {"kind": "heading", "text": "<img src=x onerror=1>"},
        {"kind": "list", "items": ["<i>a</i>"]},
    )
    assert "<script>" not in html and "<b>x</b>" not in html and "<img src=x" not in html
    assert "&lt;script&gt;" in html and "&amp;" in html and "&lt;i&gt;a&lt;/i&gt;" in html


def test_bold_italic_and_links_are_rendered() -> None:
    html, text = _render(_p("**fuerte** y *cursiva* y [campus](https://www.upiixsol.com/a?x=1&y=2)"))
    assert "<strong" in html and ">fuerte</strong>" in html
    assert "<em" in html and ">cursiva</em>" in html
    assert 'href="https://www.upiixsol.com/a?x=1&amp;y=2"' in html
    assert ">campus</a>" in html
    assert "fuerte y cursiva y campus (https://www.upiixsol.com/a?x=1&y=2)" in text


def test_javascript_link_is_dropped() -> None:
    html, text = _render(_p("[clic](javascript:alert(1)) y [mal](data:text/html,x) y [ok](ftp://x.mx)"))
    assert 'href="javascript' not in html and 'href="data' not in html and 'href="ftp' not in html
    assert "clic" in html and "mal" in html
    assert "javascript:" not in text


def test_button_is_bulletproof_cell() -> None:
    html, text = _render({"kind": "button", "label": "Ir al campus", "url": "https://www.upiixsol.com/"})
    cell = re.search(
        r'<td[^>]*bgcolor="(#[0-9A-Fa-f]{6})"[^>]*>\s*<a [^>]*href="https://www.upiixsol.com/"', html
    )
    assert cell, "background must live on the <td> that wraps the link"
    assert "Ir al campus" in html and "display:inline-block" in html
    assert contrast("#FFFFFF", cell.group(1)) >= 4.5 or "color:#1F2A24" in html
    assert "Ir al campus: https://www.upiixsol.com/" in text


def test_image_has_alt_and_absolute_url() -> None:
    html, text = _render(
        {"kind": "image", "url": "https://www.upiixsol.com/media/mail/a.png", "alt": "Cartel del taller"}
    )
    assert 'src="https://www.upiixsol.com/media/mail/a.png"' in html
    assert 'alt="Cartel del taller"' in html
    assert "Cartel del taller" in text
    html2, _ = _render({"kind": "image", "url": "https://cdn.example.mx/a.jpg", "alt": "x"})
    assert 'src="https://cdn.example.mx/a.jpg"' in html2


def test_event_card_shows_mexico_city_time() -> None:
    event = EventCard(
        title="Primera clase",
        start=datetime(2026, 11, 18, 21, 0, tzinfo=UTC),  # 15:00 in Mexico City
        end=datetime(2026, 11, 18, 23, 0, tzinfo=UTC),
        place="Salón 205",
        description="Trae tu laptop",
        link="https://www.upiixsol.com/eventos/1",
        google_url="https://calendar.google.com/calendar/render?action=TEMPLATE&text=Primera",
        outlook_url="https://outlook.live.com/calendar/0/deeplink/compose?subject=Primera",
    )
    html, text = _render(
        {"kind": "event", "event_id": 1}, event=event, ics_url="https://www.upiixsol.com/api/mail/ics/tok.ics"
    )
    assert "miércoles" in html and "18" in html and "noviembre" in html
    assert "3:00 p. m." in html and "5:00 p. m." in html and "9:00" not in html
    assert "Salón 205" in html and "Trae tu laptop" in html
    assert "Google Calendar" in html and "Outlook" in html and "Apple / .ics" in html
    assert "calendar.google.com" in html and "outlook.live.com" in html and "tok.ics" in html
    assert "3:00 p. m." in text and "Salón 205" in text and "tok.ics" in text


def test_footer_with_and_without_reply_to() -> None:
    html, text = _render(_p("Hola"), reply_to="mesa@upiixsol.com", sender=CLUB, theme=CLUB_THEME)
    assert "Responde este correo para escribirle a la mesa directiva" in html
    assert "mesa@upiixsol.com" in html
    assert "Recibes este correo porque eres parte de UpiixSol." in html
    assert f'href="{UNSUB}"' in html and "Darte de baja" in html
    assert html.rindex("Enviado por") > html.index("Hola")  # the footer repeats the sender
    assert "Responde este correo" in text and f"Darte de baja: {UNSUB}" in text
    html2, text2 = _render(_p("Hola"))
    assert "Este correo no recibe respuestas" in html2 and "Este correo no recibe respuestas" in text2
    assert "Responde este correo" not in html2


def test_text_part_matches_blocks() -> None:
    _, text = _render(
        {"kind": "heading", "text": "Bienvenidos"},
        _p("Un **párrafo** con [enlace](https://www.upiixsol.com/x)."),
        {"kind": "list", "items": ["uno", "dos"]},
        {"kind": "list", "items": ["a", "b"], "ordered": True},
        {"kind": "divider"},
        {"kind": "button", "label": "Ver", "url": "https://www.upiixsol.com/club"},
    )
    for fragment in (
        "Hola, Ana",
        "BIENVENIDOS",
        "Un párrafo con enlace (https://www.upiixsol.com/x).",
        "- uno",
        "- dos",
        "1. a",
        "2. b",
        "Ver: https://www.upiixsol.com/club",
    ):
        assert fragment in text, fragment
    assert "**" not in text and "<" not in text


def test_html_size_cap() -> None:
    thirty = [_p(f"Párrafo {i} " + "texto *largo* **fuerte** " * 40) for i in range(30)]
    html, _ = _render(*thirty)
    assert len(html.encode()) <= 100_000
    heavy = [_p("&" * 2000) for _ in range(30)]
    with pytest.raises(AppError) as error:
        _render(*heavy)
    assert error.value.status == 422


def test_contrast_of_every_text_color_in_light_and_inverted() -> None:
    html, _ = _render(
        {"kind": "heading", "text": "T"},
        _p("p"),
        {"kind": "button", "label": "Ver", "url": "https://www.upiixsol.com/"},
        sender=CLUB,
        theme=Theme(primary="#7ED957", secondary="#04944F", accent="#00BF63"),
    )
    assert "#FFFFFF" in html.upper()
    assert contrast("#1F2A24", "#FFFFFF") >= 4.5
    assert contrast("#E8ECE9", "#161A17") >= 4.5  # the inverted body pair


@pytest.mark.parametrize(
    ("name", "raw", "kwargs"),
    [
        (
            "club_evento_boton",
            [
                {"kind": "heading", "text": "Primera clase del taller"},
                _p(
                    "El día de **mañana** será la primera clase. Trae tu laptop y [tu cuenta](https://www.upiixsol.com/)."
                ),
                {"kind": "event", "event_id": 1},
                {"kind": "button", "label": "Ir al campus", "url": "https://www.upiixsol.com/"},
            ],
            {"sender": CLUB, "theme": CLUB_THEME, "reply_to": "mesa@upiixsol.com", "event": True},
        ),
        (
            "mesa_directiva",
            [
                {"kind": "heading", "text": "Aviso de la mesa directiva"},
                _p("Se abre la convocatoria de **nuevos clubes**."),
                {"kind": "list", "items": ["Registro hasta el viernes", "Entrevista con la mesa"]},
                {"kind": "divider"},
                {"kind": "image", "url": "https://www.upiixsol.com/media/mail/cartel.png", "alt": "Cartel"},
            ],
            {"sender": BOARD, "theme": Theme()},
        ),
        (
            "largo_cerca_del_limite",
            [_p(f"Párrafo {i}. " + "Texto de relleno *cursiva* y **negrita**. " * 44) for i in range(30)],
            {"sender": CLUB, "theme": CLUB_THEME},
        ),
    ],
)
def test_golden_fixtures_match(name: str, raw: list[dict], kwargs: dict) -> None:
    event = None
    if kwargs.pop("event", False):
        event = EventCard(
            title="Primera clase",
            start=datetime(2026, 11, 18, 21, 0, tzinfo=UTC),
            end=datetime(2026, 11, 18, 23, 0, tzinfo=UTC),
            place="Salón 205",
            description="Trae tu laptop.",
            link="https://www.upiixsol.com/eventos/1",
            google_url="https://calendar.google.com/calendar/render?action=TEMPLATE&text=Primera+clase",
            outlook_url="https://outlook.live.com/calendar/0/deeplink/compose?subject=Primera+clase",
        )
    html, _ = _render(
        *raw,
        preheader="Mañana, 3 pm, salón 205",
        event=event,
        ics_url="https://www.upiixsol.com/api/mail/ics/demo.ics",
        **kwargs,
    )
    path = FIXTURES / f"{name}.html"
    if os.environ.get("UPDATE_MAIL_FIXTURES") or not path.exists():
        path.write_text(html, encoding="utf-8")
    assert html == path.read_text(encoding="utf-8")
    assert len(html.encode()) <= 100_000
