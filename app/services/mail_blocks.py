"""Email blocks (UPS-085, spec 004): what a campaign body is made of, validated once for preview and send.

    blocks = Blocks.model_validate(raw_list).root         # list[Block]; ValidationError with Spanish messages
    stored = Blocks(blocks).model_dump(mode="json")       # JSON for mail_campaigns.content
    reply_to = reply_to_adapter.validate_python(value)    # one lowercase address, never CR/LF

Blocks are a discriminated union on `kind`: heading, paragraph, list, button, event, image, divider. Every
model forbids extra fields and there is no raw-HTML block. Inline formatting (`**b**`, `*i*`, `[t](url)`)
lives in the text and is escaped by the renderer (UPS-086). Event times typed without an offset are
America/Mexico_City (UTC-6, no DST since 2022) and every event datetime is stored in UTC, so a typed 15:00
is `21:00Z`.
"""

import re
from datetime import UTC, datetime, timedelta, timezone
from typing import Annotated, Any, Literal

from email_validator import EmailNotValidError, validate_email
from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Discriminator,
    RootModel,
    Tag,
    TypeAdapter,
    field_validator,
    model_validator,
)

from app.sanitize import safe_url

MEXICO_CITY = timezone(timedelta(hours=-6), "America/Mexico_City")
MAX_BLOCKS = 30
MAX_URL = 2000
_UNSAFE_ADDRESS = re.compile(r"[\s,;<>\"'()\[\]\\\x00-\x1f\x7f]")


def _text(value: Any, label: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} debe ser texto.")
    value = value.strip()
    if not value:
        raise ValueError(f"{label} no puede estar vacío.")
    if len(value) > maximum:
        raise ValueError(f"{label} admite hasta {maximum} caracteres.")
    return value


def _optional_text(value: Any, label: str, maximum: int) -> str | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    return _text(value, label, maximum)


def _url(value: Any, label: str) -> str:
    text = _text(value, label, MAX_URL)
    try:
        return safe_url(text)
    except ValueError:
        raise ValueError(f"{label} debe empezar con http:// o https://") from None


def _to_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=MEXICO_CITY)
    return value.astimezone(UTC)


UtcDateTime = Annotated[datetime | None, AfterValidator(_to_utc)]


class _Block(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="before")
    @classmethod
    def _known_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            extra = sorted(set(data) - set(cls.model_fields))
            if extra:
                raise ValueError(f"Campo no permitido en el bloque: {', '.join(map(str, extra))}.")
        return data


class HeadingBlock(_Block):
    kind: Literal["heading"]
    text: str

    @field_validator("text", mode="before")
    @classmethod
    def _check_text(cls, value: Any) -> str:
        return _text(value, "El título", 120)


class ParagraphBlock(_Block):
    kind: Literal["paragraph"]
    text: str

    @field_validator("text", mode="before")
    @classmethod
    def _check_text(cls, value: Any) -> str:
        return _text(value, "El párrafo", 2000)


class ListBlock(_Block):
    kind: Literal["list"]
    items: list[str]
    ordered: bool = False

    @field_validator("items", mode="before")
    @classmethod
    def _check_items(cls, value: Any) -> list[str]:
        if not isinstance(value, list) or not 1 <= len(value) <= 20:
            raise ValueError("La lista lleva de 1 a 20 elementos.")
        return [_text(item, "Cada elemento de la lista", 300) for item in value]


class ButtonBlock(_Block):
    kind: Literal["button"]
    label: str
    url: str

    @field_validator("label", mode="before")
    @classmethod
    def _check_label(cls, value: Any) -> str:
        return _text(value, "El texto del botón", 40)

    @field_validator("url", mode="before")
    @classmethod
    def _check_url(cls, value: Any) -> str:
        return _url(value, "El enlace del botón")


class EventBlock(_Block):
    """A campus event by `event_id` (resolved from the DB at send time) or typed title, start and end."""

    kind: Literal["event"]
    event_id: int | None = None
    title: str | None = None
    start: UtcDateTime = None
    end: UtcDateTime = None
    place: str | None = None
    description: str | None = None
    link: str | None = None
    # A template slot (UPS-100): valid in templates and preview, drawn as a sample card, refused on send.
    placeholder: bool = False

    @field_validator("event_id", mode="before")
    @classmethod
    def _check_id(cls, value: Any) -> Any:
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 1):
            raise ValueError("El evento del campus no es válido.")
        return value

    @field_validator("title", mode="before")
    @classmethod
    def _check_title(cls, value: Any) -> str | None:
        return _optional_text(value, "El título del evento", 120)

    @field_validator("place", mode="before")
    @classmethod
    def _check_place(cls, value: Any) -> str | None:
        return _optional_text(value, "El lugar", 200)

    @field_validator("description", mode="before")
    @classmethod
    def _check_description(cls, value: Any) -> str | None:
        return _optional_text(value, "La descripción del evento", 2000)

    @field_validator("link", mode="before")
    @classmethod
    def _check_link(cls, value: Any) -> str | None:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        return _url(value, "El enlace del evento")

    @model_validator(mode="after")
    def _id_or_typed(self) -> "EventBlock":
        typed = (self.title, self.start, self.end, self.place, self.description, self.link)
        if self.placeholder:
            if self.event_id is not None or any(value is not None for value in typed):
                raise ValueError(
                    "Un evento de ejemplo no lleva datos: completa el evento o quita el ejemplo."
                )
            return self
        if self.event_id is not None:
            if any(value is not None for value in typed):
                raise ValueError("Elige un evento del campus o escribe uno, no ambos.")
            return self
        if self.title is None or self.start is None or self.end is None:
            raise ValueError("El evento necesita título, inicio y fin, o un evento del campus.")
        if self.end <= self.start:
            raise ValueError("La hora de fin debe ser posterior a la de inicio.")
        return self


class ImageBlock(_Block):
    kind: Literal["image"]
    url: str
    alt: str
    link: str | None = None  # optional click-through (UPS-091)

    @field_validator("link", mode="before")
    @classmethod
    def _check_link(cls, value: Any) -> str | None:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        return _url(value, "El enlace de la imagen")

    @field_validator("url", mode="before")
    @classmethod
    def _check_url(cls, value: Any) -> str:
        return _url(value, "La URL de la imagen")

    @field_validator("alt", mode="before")
    @classmethod
    def _check_alt(cls, value: Any) -> str:
        return _text(value, "El texto alternativo de la imagen", 200)


class DividerBlock(_Block):
    kind: Literal["divider"]


def _kind(value: Any) -> str | None:
    kind = value.get("kind") if isinstance(value, dict) else getattr(value, "kind", None)
    return kind if isinstance(kind, str) else None


Block = Annotated[
    Annotated[HeadingBlock, Tag("heading")]
    | Annotated[ParagraphBlock, Tag("paragraph")]
    | Annotated[ListBlock, Tag("list")]
    | Annotated[ButtonBlock, Tag("button")]
    | Annotated[EventBlock, Tag("event")]
    | Annotated[ImageBlock, Tag("image")]
    | Annotated[DividerBlock, Tag("divider")],
    Discriminator(
        _kind,
        custom_error_type="block_kind",
        custom_error_message="Tipo de bloque no válido.",
    ),
]


class Blocks(RootModel[list[Block]]):
    """1–30 blocks, at most one `event`."""

    @model_validator(mode="after")
    def _limits(self) -> "Blocks":
        if not self.root:
            raise ValueError("Agrega al menos un bloque.")
        if len(self.root) > MAX_BLOCKS:
            raise ValueError(f"Un correo admite hasta {MAX_BLOCKS} bloques.")
        if sum(isinstance(block, EventBlock) for block in self.root) > 1:
            raise ValueError("Un correo admite un solo evento.")
        return self


def _reply_to(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("Escribe un solo correo válido.")
    if any(char in value for char in "\r\n\x00"):
        raise ValueError("El correo de respuesta debe ser una sola línea.")
    value = value.strip()
    if not value or len(value) > 254 or _UNSAFE_ADDRESS.search(value):
        raise ValueError("Escribe un solo correo válido, sin saltos de línea.")
    try:
        return validate_email(value, check_deliverability=False).normalized.lower()
    except EmailNotValidError:
        raise ValueError("Escribe un solo correo válido.") from None


ReplyTo = Annotated[str, BeforeValidator(_reply_to)]
reply_to_adapter: TypeAdapter[str] = TypeAdapter(ReplyTo)
