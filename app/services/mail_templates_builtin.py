"""Built-in email templates (UPS-100, spec 005): four starting points, read-only, validated at import.

    for template in BUILTIN_TEMPLATES: template.blocks      # list[dict], same JSON as mail_campaigns.content
    builtin_by_id("builtin:anuncio")

Spanish placeholders only: no real names, dates or addresses. Buttons point to `https://example.com`
(a reserved domain) so the sender must replace them; the event slot is an event `placeholder`, which
previews as a sample card and is refused on create/send until a real event replaces it (UPS-101).
Ids are `builtin:<slug>`; they are never stored in `mail_templates`.
"""

from dataclasses import dataclass
from typing import Any

from app.services.mail_blocks import Blocks

PLACEHOLDER_URL = "https://example.com"
_EVENT: dict[str, Any] = {"kind": "event", "placeholder": True}


@dataclass(frozen=True)
class BuiltinTemplate:
    slug: str
    name: str
    description: str
    subject: str
    preheader: str
    blocks: list[dict[str, Any]]

    @property
    def id(self) -> str:
        return f"builtin:{self.slug}"


def _build(slug: str, name: str, description: str, subject: str, preheader: str, raw: list[dict[str, Any]]):
    # Validate and keep the normalized JSON, so what the API serves is exactly what a campaign would store.
    blocks = [block.model_dump(mode="json") for block in Blocks.model_validate(raw).root]
    return BuiltinTemplate(slug, name, description, subject, preheader, blocks)


BUILTIN_TEMPLATES: tuple[BuiltinTemplate, ...] = (
    _build(
        "anuncio",
        "Anuncio",
        "Una noticia breve con un botón para saber más.",
        "Escribe aquí el asunto del anuncio",
        "Una línea que se ve junto al asunto en la bandeja de entrada",
        [
            {"kind": "heading", "text": "Escribe aquí el título"},
            {
                "kind": "paragraph",
                "text": "Cuenta la novedad en dos o tres frases: **qué** pasa, **para quién** es y "
                "por qué vale la pena enterarse.",
            },
            {"kind": "button", "label": "Quiero saber más", "url": PLACEHOLDER_URL},
            {"kind": "divider"},
            {
                "kind": "paragraph",
                "text": "¿Dudas? Responde este correo y te ayudamos.",
            },
        ],
    ),
    _build(
        "invitacion-evento",
        "Invitación a evento",
        "Invita a un evento con su tarjeta de fecha, lugar y calendario.",
        "Te invitamos: escribe aquí el nombre del evento",
        "Guarda la fecha y confirma tu lugar",
        [
            {"kind": "heading", "text": "Estás invitado"},
            {
                "kind": "paragraph",
                "text": "Escribe aquí una invitación corta: de qué trata el evento y qué se van a llevar.",
            },
            _EVENT,
            {"kind": "button", "label": "Confirmar asistencia", "url": PLACEHOLDER_URL},
            {"kind": "paragraph", "text": "Te esperamos. Invita a quien quieras."},
        ],
    ),
    _build(
        "recordatorio",
        "Recordatorio",
        "Recuerda un evento próximo y lo que hay que llevar.",
        "Recordatorio: escribe aquí el nombre del evento",
        "Falta poco: esto es lo que necesitas saber",
        [
            {"kind": "heading", "text": "Te lo recordamos"},
            {"kind": "paragraph", "text": "Escribe aquí un recordatorio amable: falta poco para el evento."},
            _EVENT,
            {"kind": "heading", "text": "Antes de llegar"},
            {
                "kind": "list",
                "items": [
                    "Escribe aquí lo primero que deben llevar",
                    "Escribe aquí lo segundo",
                    "Escribe aquí cualquier otra indicación",
                ],
            },
            {"kind": "button", "label": "Ver detalles", "url": PLACEHOLDER_URL},
        ],
    ),
    _build(
        "nueva-clase-boletin",
        "Nueva clase / boletín",
        "Comparte lo nuevo del club: una clase, una ruta o las noticias del periodo.",
        "Novedades del club: escribe aquí el asunto",
        "Esto es lo nuevo que preparamos para ti",
        [
            {"kind": "heading", "text": "Lo nuevo en el club"},
            {
                "kind": "paragraph",
                "text": "Escribe aquí una introducción breve: qué estrenamos y por qué te puede servir.",
            },
            {"kind": "divider"},
            {"kind": "heading", "text": "Nueva clase"},
            {"kind": "paragraph", "text": "Escribe aquí de qué trata la clase y qué aprenderán."},
            {"kind": "button", "label": "Ir a la clase", "url": PLACEHOLDER_URL},
            {"kind": "divider"},
            {"kind": "heading", "text": "También en este boletín"},
            {
                "kind": "list",
                "items": [
                    "Escribe aquí la primera noticia",
                    "Escribe aquí la segunda noticia",
                    "Escribe aquí la tercera noticia",
                ],
            },
        ],
    ),
)


def builtin_by_id(template_id: str) -> BuiltinTemplate | None:
    return next((template for template in BUILTIN_TEMPLATES if template.id == template_id), None)
