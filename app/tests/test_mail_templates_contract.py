"""Mail templates contract (UPS-100, spec 005): table, built-ins, event placeholder, canvas theme."""

import logging
import re
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import MailTemplate
from app.services.mail_blocks import Blocks, EventBlock
from app.services.mail_render import CampaignLike, Sender, Theme, canvas_theme, render_blocks
from app.services.mail_templates_builtin import BUILTIN_TEMPLATES, builtin_by_id
from app.tests.conftest import make_academy

UNSUB = "%recipient.unsubscribe_url%"
BLOCK = [{"kind": "paragraph", "text": "Hola"}]


def _template(name: str, scope: str = "site", academy_id: int | None = None) -> MailTemplate:
    return MailTemplate(scope=scope, academy_id=academy_id, name=name, subject="Asunto", content=BLOCK)


def test_mail_templates_migration_round_trips_on_sqlite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from alembic import command
    from alembic.config import Config

    from app.config import get_settings

    url = f"sqlite:///{tmp_path / 'templates.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    engine = create_engine(url)
    loggers = [
        logger for logger in logging.root.manager.loggerDict.values() if isinstance(logger, logging.Logger)
    ]
    disabled = {logger: logger.disabled for logger in loggers}
    try:
        config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
        command.upgrade(config, "head")
        inspector = inspect(engine)
        assert "mail_templates" in inspector.get_table_names()
        with engine.connect() as conn:  # SQLAlchemy cannot reflect expression indexes: ask SQLite
            found = conn.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type = 'index' "
                "AND name = 'uq_mail_templates_scope_academy_name'"
            ).all()
        assert found
        command.downgrade(config, "0010")
        names = set(inspect(engine).get_table_names())
        assert "mail_templates" not in names and "mail_campaigns" in names  # additive: only ours dropped
        command.downgrade(config, "base")
        command.upgrade(config, "head")
    finally:
        engine.dispose()
        get_settings.cache_clear()
        for logger, was_disabled in disabled.items():
            logger.disabled = was_disabled


def test_template_name_unique_per_scope_case_insensitive(db: Session):
    club, other = make_academy(db, "ia", "IA"), make_academy(db, "ux", "UX")
    db.add(_template("Bienvenida"))
    db.add(_template("Bienvenida", "academy", club.id))  # same name in a club is fine
    db.add(_template("bienvenida", "academy", other.id))  # and in another club
    db.flush()
    for duplicate in (_template("BIENVENIDA"), _template("BIENVENIDA", "academy", club.id)):
        db.add(duplicate)
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()


def test_template_scope_and_club_must_agree(db: Session):
    club = make_academy(db, "ia", "IA")
    for bad in (_template("A", "site", club.id), _template("B", "academy", None), _template("C", "otro")):
        db.add(bad)
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()


def test_builtin_templates_validate_as_blocks():
    for template in BUILTIN_TEMPLATES:
        assert Blocks.model_validate(template.blocks).root, template.id
        assert template.subject and template.preheader and template.description
        assert len(template.name) <= 60 and len(template.description) <= 140
        assert len(template.subject) <= 150 and len(template.preheader) <= 140
        assert template.id == f"builtin:{template.slug}"


def test_builtin_templates_have_no_real_names_dates_or_addresses():
    for template in BUILTIN_TEMPLATES:
        text = repr(template.blocks) + template.subject + template.preheader
        assert "@" not in text, template.id
        assert not re.search(r"\b(19|20)\d\d\b|\d{1,2}[/:]\d{1,2}", text), template.id
        urls = set(re.findall(r"https?://[^\s'\"]+", text))
        assert urls <= {"https://example.com"}, template.id
        for block in Blocks.model_validate(template.blocks).root:
            if isinstance(block, EventBlock):  # no typed event data, only the placeholder
                assert block.placeholder and block.title is None and block.start is None


def test_builtins_are_anuncio_invitacion_recordatorio_boletin():
    assert [t.name for t in BUILTIN_TEMPLATES] == [
        "Anuncio",
        "Invitación a evento",
        "Recordatorio",
        "Nueva clase / boletín",
    ]
    assert len({t.id for t in BUILTIN_TEMPLATES}) == 4
    assert builtin_by_id("builtin:anuncio") is BUILTIN_TEMPLATES[0]
    assert builtin_by_id("builtin:nope") is None
    with_event = {t.slug for t in BUILTIN_TEMPLATES if any(b["kind"] == "event" for b in t.blocks)}
    assert with_event == {"invitacion-evento", "recordatorio"}


def _render(blocks: list[dict]) -> tuple[str, str]:
    campaign = CampaignLike("Asunto", Blocks.model_validate(blocks).root, "Pre")
    return render_blocks(
        campaign, sender=Sender(), theme=Theme(), recipient_name="Ana", unsubscribe_href=UNSUB
    )


def test_event_placeholder_block_validates_and_renders_a_sample_card():
    assert Blocks.model_validate([{"kind": "event", "placeholder": True}]).root[0].placeholder
    for typed in (
        {"kind": "event", "placeholder": True, "event_id": 3},
        {"kind": "event", "placeholder": True, "title": "X"},
    ):
        with pytest.raises(ValidationError):
            Blocks.model_validate([typed])
    with pytest.raises(ValidationError):  # without the flag the old rules still apply
        Blocks.model_validate([{"kind": "event"}])
    html, text = _render([{"kind": "event", "placeholder": True}])
    assert "Título del evento" in html and "Lugar del evento" in html and "Día y hora" in html
    assert "Título del evento" in text and "Día y hora" in text
    assert "2000" not in html and "Calendar" not in html  # no fake date, no calendar links


def test_every_builtin_renders_without_error():
    for template in BUILTIN_TEMPLATES:
        html, text = _render(template.blocks)
        assert "Escribe aquí" in html and "escribe aquí" in text.lower(), template.id


def test_preview_theme_matches_render_theme():
    theme = Theme(primary="#7ED957", secondary="#04944F", accent="#00BF63", site_logo_url="/media/logo.png")
    sender = Sender("UpiixIA", "/media/club.png")
    canvas = canvas_theme(sender, theme)
    campaign = CampaignLike("Asunto", Blocks.model_validate(BLOCK).root)
    html, _ = render_blocks(
        campaign, sender=sender, theme=theme, recipient_name="Ana", unsubscribe_href=UNSUB
    )
    colors = canvas["colors"]
    assert (colors["primary"], colors["secondary"], colors["accent"]) == ("#7ED957", "#04944F", "#00BF63")
    for value in (colors["primary"], colors["ink"], colors["page"], colors["line"], canvas["font"]):
        assert value in html
    assert canvas["sender"] == {
        "label": "Enviado por",
        "name": "UpiixIA",
        "logo_url": canvas["sender"]["logo_url"],
    }
    assert canvas["sender"]["logo_url"].endswith("/media/club.png") and canvas["sender"]["logo_url"] in html
    assert canvas["site_logo_url"].endswith("/media/logo.png") and canvas["site_logo_url"] in html
    board = canvas_theme(Sender(), Theme(primary="nope"))  # same fallback as the renderer
    assert board["colors"]["primary"] == canvas_theme(Sender(), Theme())["colors"]["primary"]
    assert board["sender"]["label"] == "Enviado por la mesa directiva de"
