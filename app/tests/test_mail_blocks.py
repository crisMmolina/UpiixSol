"""Email blocks contract (UPS-085, spec 004): kinds, limits, event times, URLs, Reply-To, migration 0010."""

import logging
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, inspect

from app.services.mail_blocks import Blocks, reply_to_adapter

EVENT = {
    "kind": "event",
    "title": "Primera clase",
    "start": "2026-11-18T15:00:00",
    "end": "2026-11-18T17:00:00",
}
EACH_KIND = [
    {"kind": "heading", "text": "Hola"},
    {"kind": "paragraph", "text": "Texto con **negritas** y [campus](https://www.upiixsol.com)"},
    {"kind": "list", "items": ["Uno", "Dos"], "ordered": True},
    {"kind": "button", "label": "Ir al campus", "url": "https://www.upiixsol.com/"},
    EVENT,
    {"kind": "image", "url": "https://www.upiixsol.com/media/mail/a.jpg", "alt": "Portada"},
    {"kind": "divider"},
]


def parse(raw: list[dict]) -> list:
    return Blocks.model_validate(raw).root


def messages(error: ValidationError) -> str:
    return " | ".join(e["msg"] for e in error.errors())


def test_blocks_accept_each_kind():
    blocks = parse(EACH_KIND)
    assert [block.kind for block in blocks] == [b["kind"] for b in EACH_KIND]
    assert blocks[2].ordered is True
    assert Blocks(blocks).model_dump(mode="json")  # stored as JSON on the campaign


def test_blocks_reject_unknown_kind_and_extra_fields():
    with pytest.raises(ValidationError):
        parse([{"kind": "html", "html": "<script>alert(1)</script>"}])
    with pytest.raises(ValidationError):
        parse([{"kind": "paragraph", "text": "hola", "style": "color:red"}])
    with pytest.raises(ValidationError):
        parse([{"kind": "paragraph", "text": ""}])
    with pytest.raises(ValidationError) as caught:
        parse([{"kind": "button", "label": "x" * 41, "url": "https://www.upiixsol.com"}])
    assert "40" in messages(caught.value)  # Spanish message with the limit


def test_blocks_limit_30_and_one_event():
    paragraph = {"kind": "paragraph", "text": "hola"}
    assert len(parse([paragraph] * 30)) == 30
    with pytest.raises(ValidationError) as caught:
        parse([paragraph] * 31)
    assert "30" in messages(caught.value)
    with pytest.raises(ValidationError) as caught:
        parse([])
    assert "al menos" in messages(caught.value)
    with pytest.raises(ValidationError) as caught:
        parse([EVENT, EVENT])
    assert "un solo evento" in messages(caught.value)


def test_event_block_needs_event_id_or_title_start_end():
    assert parse([{"kind": "event", "event_id": 7}])[0].event_id == 7
    for incomplete in (
        {"kind": "event"},
        {"kind": "event", "title": "Solo título"},
        {"kind": "event", "title": "x", "start": "2026-11-18T15:00:00"},
        {"kind": "event", "event_id": 7, "title": "Mezcla"},
    ):
        with pytest.raises(ValidationError):
            parse([incomplete])


def test_event_end_after_start():
    for end in ("2026-11-18T15:00:00", "2026-11-18T14:00:00"):
        with pytest.raises(ValidationError) as caught:
            parse([{**EVENT, "end": end}])
        assert "posterior" in messages(caught.value)


def test_typed_event_naive_time_is_mexico_city():
    event = parse([EVENT])[0]
    assert event.start == datetime(2026, 11, 18, 21, 0, tzinfo=UTC)  # typed 15:00 is 21:00Z
    assert event.end == datetime(2026, 11, 18, 23, 0, tzinfo=UTC)
    with_offset = parse([{**EVENT, "start": "2026-11-18T15:00:00-05:00", "end": "2026-11-18T17:00:00-05:00"}])
    assert with_offset[0].start == datetime(2026, 11, 18, 20, 0, tzinfo=UTC)
    stored = Blocks(parse([EVENT])).model_dump(mode="json")[0]
    assert stored["start"].endswith("Z") or stored["start"].endswith("+00:00")


@pytest.mark.parametrize(
    "block",
    [
        {"kind": "button", "label": "Ir", "url": "javascript:alert(1)"},
        {"kind": "button", "label": "Ir", "url": "/relativo"},
        {"kind": "image", "url": "data:image/png;base64,AAAA", "alt": "x"},
        {"kind": "image", "url": "ftp://example.com/a.png", "alt": "x"},
        {**EVENT, "link": "javascript:alert(1)"},
    ],
)
def test_button_and_image_urls_must_be_http(block):
    with pytest.raises(ValidationError):
        parse([block])


def test_reply_to_with_newline_is_422():
    assert reply_to_adapter.validate_python(" Mesa@IPN.mx ") == "mesa@ipn.mx"
    for bad in ("a@b.mx\nBcc: x@y.mx", "a@b.mx\r\n", "a@b.mx, c@d.mx", "no-es-correo", "Mesa <a@b.mx>"):
        with pytest.raises(ValidationError):
            reply_to_adapter.validate_python(bad)


def test_mail_blocks_migration_round_trips_on_sqlite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from alembic import command
    from alembic.config import Config

    from app.config import get_settings

    url = f"sqlite:///{tmp_path / 'blocks.db'}"  # a temp file only, never the dotenv DATABASE_URL
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    engine = create_engine(url)
    loggers = [
        logger for logger in logging.root.manager.loggerDict.values() if isinstance(logger, logging.Logger)
    ]
    disabled = {logger: logger.disabled for logger in loggers}
    new = {"content", "sender_academy_id", "preheader", "reply_to", "ics_token"}
    try:
        config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
        command.upgrade(config, "head")
        columns = {c["name"] for c in inspect(engine).get_columns("mail_campaigns")}
        assert new <= columns
        assert any(
            index["unique"] and index["column_names"] == ["ics_token"]
            for index in inspect(engine).get_indexes("mail_campaigns")
        ) or any(
            constraint["column_names"] == ["ics_token"]
            for constraint in inspect(engine).get_unique_constraints("mail_campaigns")
        )
        command.downgrade(config, "0009")
        columns = {c["name"] for c in inspect(engine).get_columns("mail_campaigns")}
        assert not new & columns and "body" in columns  # additive: 0009 is intact
        command.downgrade(config, "base")
        command.upgrade(config, "head")
    finally:
        engine.dispose()
        get_settings.cache_clear()
        for logger, was_disabled in disabled.items():
            logger.disabled = was_disabled
