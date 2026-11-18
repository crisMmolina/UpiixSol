"""Email renderer (UPS-086, spec 004 §Content and rendering): blocks to one HTML part and one plain-text part.

    theme = theme_for(get_site(db), club_colors=(club.color_primary, club.color_secondary, club.color_accent))
    html, text = render_blocks(campaign_like, sender=Sender("UpiixIA", club.logo_url), theme=theme,
        recipient_name="%recipient.name%", unsubscribe_href="%recipient.unsubscribe_url%",
        event=resolved_event_card, ics_url=public_ics_url)

One renderer for the preview and for sending. Hand-written table layout (600 px), inline styles only, no
CSS inliner. Everything the sender typed is escaped first; `**b**`, `*i*` and `[t](url)` are parsed after,
links only when `app.sanitize.safe_url` accepts them. Colors that reach a `style` come only from
`_hex()`-checked values.

Dark mode: Gmail (iOS/Android) forces its own inversion and ignores `color-scheme`, so nothing depends on it:
the UpiixSol logo is a transparent PNG with mid-tone colors that read on light and dark, no text is baked
into images, text colors are ink-on-white (`#1F2A24`/`#FFFFFF`) pairs that stay AA after a plain inversion
(`contrast()`), and buttons carry their own background on the `<td>` with a text color picked by contrast.
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from html import escape
from urllib.parse import urlsplit

from app.config import get_settings
from app.errors import AppError
from app.sanitize import safe_url
from app.services.mail_blocks import (
    Block,
    ButtonBlock,
    DividerBlock,
    EventBlock,
    HeadingBlock,
    ImageBlock,
    ListBlock,
    ParagraphBlock,
)
from app.services.site import DEFAULTS, SiteOut

MAX_HTML_BYTES = 100_000  # Gmail clips longer messages
MEXICO_CITY = timezone(timedelta(hours=-6), "America/Mexico_City")

INK = "#1F2A24"
MUTED = "#5A645E"
PAGE = "#F3F1EA"
CARD = "#FFFFFF"
TINT = "#F7F6F0"
LINE = "#E4E1D6"
FONT = "-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"

_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
_LINK = re.compile(r"\[([^\[\]]{1,300})\]\(((?:[^()\s]|\([^()\s]*\)){1,2000})\)")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_ITALIC = re.compile(r"\*(.+?)\*")
_TOKEN = re.compile("(\\d+)")
_WEEKDAYS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
_MONTHS = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)  # fmt: skip


@dataclass(frozen=True)
class Sender:
    """Who sends it: a club (`name` set, optional logo) or the board (`name` None)."""

    name: str | None = None
    logo_url: str | None = None


@dataclass(frozen=True)
class Theme:
    site_name: str = str(DEFAULTS["name"])
    site_logo_url: str | None = DEFAULTS["logo_url"]
    primary: str = str(DEFAULTS["color_primary"])
    secondary: str = str(DEFAULTS["color_secondary"])
    accent: str = str(DEFAULTS["color_accent"])


@dataclass(frozen=True)
class EventCard:
    """An event resolved for the card (title, UTC times, optional fields and the Google/Outlook links)."""

    title: str
    start: datetime
    end: datetime
    place: str | None = None
    description: str | None = None
    link: str | None = None
    cover_url: str | None = None
    google_url: str | None = None
    outlook_url: str | None = None


@dataclass(frozen=True)
class CampaignLike:
    """What the renderer needs of a campaign (a stored one or a preview): validated blocks and copy."""

    subject: str
    blocks: list[Block]
    preheader: str | None = None
    reply_to: str | None = None
    footer_reason: str = ""


def _hex(value: str | None, default: str) -> str:
    return value.upper() if isinstance(value, str) and _HEX.match(value) else default.upper()


def theme_for(site: SiteOut, club_colors: tuple[str, str, str] | None) -> Theme:
    """Site brand, with the sender club's colors on top when it has them (invalid colors fall back)."""
    primary, secondary, accent = club_colors or (None, None, None)
    return Theme(
        site_name=site.name,
        site_logo_url=site.logo_url,
        primary=_hex(primary, site.color_primary),
        secondary=_hex(secondary, site.color_secondary),
        accent=_hex(accent, site.color_accent),
    )


def _luminance(color: str) -> float:
    def channel(index: int) -> float:
        value = int(color[1 + index * 2 : 3 + index * 2], 16) / 255
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4

    return 0.2126 * channel(0) + 0.7152 * channel(1) + 0.0722 * channel(2)


def contrast(foreground: str, background: str) -> float:
    """WCAG contrast ratio of two `#RRGGBB` colors."""
    high, low = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def _on(background: str) -> str:
    """White or ink text, whichever reads better on `background`."""
    return "#FFFFFF" if contrast("#FFFFFF", background) >= contrast(INK, background) else INK


def _readable(color: str, background: str = CARD, minimum: float = 4.5) -> str:
    """`color` as text on `background`, or ink when it would not reach `minimum`."""
    return color if contrast(color, background) >= minimum else INK


def _base() -> str:
    return get_settings().public_base_url.rstrip("/")


def _absolute(url: str) -> str:
    if re.match(r"https?://", url, re.IGNORECASE):
        return url
    return f"{_base()}/{url.lstrip('/')}"


def _usable_image(url: str | None) -> bool:
    """Email clients do not show SVG; those fall back to a wordmark."""
    return bool(url) and not urlsplit(url).path.lower().endswith(".svg")


# ---- inline formatting ---------------------------------------------


def _inline(text: str, link_color: str) -> str:
    """Escape first, then `**b**`, `*i*`, `[t](url)`; a link `safe_url` refuses keeps only its label."""
    text = text.replace("", "").replace("", "")
    links: list[str] = []

    def stash(match: re.Match[str]) -> str:
        label = _emphasis(escape(match.group(1)))
        try:
            href = safe_url(match.group(2))
        except ValueError:
            links.append(label)
        else:
            links.append(
                f'<a href="{escape(href)}" style="color:{link_color};text-decoration:underline;'
                f'font-weight:600">{label}</a>'
            )
        return f"{len(links) - 1}"

    parts = _LINK.sub(stash, text)
    out = _emphasis(escape(parts, quote=False).replace('"', "&quot;"))
    return _TOKEN.sub(lambda m: links[int(m.group(1))], out)


def _emphasis(escaped: str) -> str:
    escaped = _BOLD.sub(r"<strong>\1</strong>", escaped)
    return _ITALIC.sub(r"<em>\1</em>", escaped)


def _plain(text: str) -> str:
    """The text part of an inline-formatted string: no markers, links as `label (url)`."""

    def link(match: re.Match[str]) -> str:
        try:
            return f"{match.group(1)} ({safe_url(match.group(2))})"
        except ValueError:
            return match.group(1)

    text = _LINK.sub(link, text)
    return _ITALIC.sub(r"\1", _BOLD.sub(r"\1", text))


# ---- dates ---------------------------------------------------------


def _clock(moment: datetime) -> str:
    hour = moment.hour % 12 or 12
    return f"{hour}:{moment.minute:02d} {'a. m.' if moment.hour < 12 else 'p. m.'}"


def _day(moment: datetime) -> str:
    return f"{_WEEKDAYS[moment.weekday()]} {moment.day} de {_MONTHS[moment.month - 1]}"


def _when(event: EventCard) -> tuple[datetime, str, str]:
    """Local start, the date line and the time line (America/Mexico_City), end date only if it differs."""
    start = event.start.astimezone(MEXICO_CITY) if event.start.tzinfo else event.start.replace(tzinfo=UTC)
    end = event.end.astimezone(MEXICO_CITY) if event.end.tzinfo else event.end.replace(tzinfo=UTC)
    start, end = start.astimezone(MEXICO_CITY), end.astimezone(MEXICO_CITY)
    span = f"{_clock(start)} – {_clock(end)}"
    if end.date() != start.date():
        span = f"{_clock(start)} – {_day(end)}, {_clock(end)}"
    return start, _day(start), f"{span} (hora de la Ciudad de México)"


# ---- html pieces ---------------------------------------------------


def _paragraph(text: str, theme: Theme) -> str:
    link = _readable(theme.secondary)
    return (
        f'<tr><td style="padding:0 32px 16px;font-family:{FONT};font-size:16px;line-height:26px;color:{INK}">'
        f"{_inline(text, link)}</td></tr>"
    ).replace("<td ", "<td ", 1)


def _heading(text: str, theme: Theme) -> str:
    return (
        f'<tr><td style="padding:8px 32px 12px;font-family:{FONT};font-size:26px;line-height:32px;'
        f'font-weight:800;color:{INK};letter-spacing:-0.3px">{_inline(text, _readable(theme.secondary))}'
        f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin-top:10px"><tr>'
        f'<td width="48" height="4" bgcolor="{theme.primary}" style="width:48px;height:4px;font-size:0;'
        f'line-height:0;background:{theme.primary};border-radius:2px">&nbsp;</td></tr></table></td></tr>'
    )


def _list(block: ListBlock, theme: Theme) -> str:
    tag = "ol" if block.ordered else "ul"
    style = "list-style-type:decimal" if block.ordered else "list-style-type:disc"
    link = _readable(theme.secondary)
    items = "".join(
        f'<li style="margin:0 0 8px;padding-left:4px;color:{INK}">{_inline(item, link)}</li>'
        for item in block.items
    )
    return (
        f'<tr><td style="padding:0 32px 16px;font-family:{FONT};font-size:16px;line-height:26px;color:{INK}">'
        f'<{tag} style="margin:0;padding-left:22px;{style}">{items}</{tag}></td></tr>'
    )


def _button(block: ButtonBlock, theme: Theme) -> str:
    color = theme.secondary
    text_color = _on(color)
    return (
        '<tr><td style="padding:8px 32px 24px">'
        '<table role="presentation" cellpadding="0" cellspacing="0"><tr>'
        f'<td align="center" bgcolor="{color}" style="background:{color};border-radius:10px">'
        f'<a href="{escape(block.url)}" style="display:inline-block;padding:14px 28px;font-family:{FONT};'
        f"font-size:16px;font-weight:700;line-height:20px;color:{text_color};text-decoration:none;"
        f'border-radius:10px">{escape(block.label)}</a></td></tr></table></td></tr>'
    )


def _image(block: ImageBlock) -> str:
    img = (
        f'<img src="{escape(_absolute(block.url))}" alt="{escape(block.alt)}" width="536" '
        'style="display:block;width:100%;max-width:536px;height:auto;border:0;border-radius:12px">'
    )
    if block.link:
        img = f'<a href="{escape(block.link)}" style="text-decoration:none">{img}</a>'
    return f'<tr><td style="padding:0 32px 20px">{img}</td></tr>'


def _divider() -> str:
    return (
        f'<tr><td style="padding:8px 32px 24px"><table role="presentation" width="100%" cellpadding="0" '
        f'cellspacing="0"><tr><td height="1" bgcolor="{LINE}" style="height:1px;font-size:0;line-height:0;'
        f'background:{LINE}">&nbsp;</td></tr></table></td></tr>'
    )


def _link_cell(label: str, href: str, theme: Theme) -> str:
    return (
        f'<a href="{escape(href)}" style="display:inline-block;margin:0 8px 8px 0;white-space:nowrap;'
        f"padding:8px 12px;border:1px solid {LINE};border-radius:8px;font-family:{FONT};font-size:13px;"
        f'font-weight:600;line-height:16px;color:{_readable(theme.secondary)};text-decoration:none">'
        f"{escape(label)}</a>"
    )


def _event_view(block: EventBlock, event: EventCard | None) -> EventCard | None:
    if event is not None:
        return event
    if block.title and block.start and block.end:
        return EventCard(
            title=block.title,
            start=block.start,
            end=block.end,
            place=block.place,
            description=block.description,
            link=block.link,
        )
    return None


def _event(event: EventCard, theme: Theme, ics_url: str | None) -> str:
    start, day_line, time_line = _when(event)
    month = _MONTHS[start.month - 1][:3].capitalize()
    badge = (
        f'<td width="64" valign="top" style="width:64px;padding:0 16px 0 0"><table role="presentation" '
        f'width="64" cellpadding="0" cellspacing="0"><tr><td align="center" bgcolor="{theme.secondary}" '
        f'style="background:{theme.secondary};border-radius:12px;padding:8px 0;font-family:{FONT};'
        f'color:{_on(theme.secondary)}"><div style="font-size:11px;line-height:14px;font-weight:700;'
        f'letter-spacing:0">{month}</div><div style="font-size:28px;line-height:32px;font-weight:800">'
        f"{start.day}</div></td></tr></table></td>"
    )
    rows = [
        f'<div style="font-size:18px;line-height:24px;font-weight:800;color:{INK}">'
        f"{escape(event.title)}</div>",
        f'<div style="font-size:14px;line-height:22px;color:{MUTED};margin-top:4px">'
        f"{escape(day_line)}<br>{escape(time_line)}</div>",
    ]
    if event.place:
        rows.append(
            f'<div style="font-size:14px;line-height:22px;color:{INK}"><strong>Lugar:</strong> '
            f"{escape(event.place)}</div>"
        )
    if event.description:
        rows.append(
            f'<div style="font-size:14px;line-height:22px;color:{INK};margin-top:8px">'
            f"{_inline(event.description, _readable(theme.secondary))}</div>"
        )
    if event.link:
        rows.append(
            f'<div style="font-size:14px;line-height:22px;margin-top:8px"><a href="{escape(event.link)}" '
            f'style="color:{_readable(theme.secondary)};font-weight:600">Ver detalles</a></div>'
        )
    links = [
        _link_cell(label, href, theme)
        for label, href in (
            ("Google Calendar", event.google_url),
            ("Outlook", event.outlook_url),
            ("Apple / .ics", ics_url),
        )
        if href
    ]
    calendar = ""
    if links:
        calendar = (
            f'<tr><td colspan="2" style="padding-top:16px;font-family:{FONT};font-size:12px;line-height:16px;'
            f'color:{MUTED}"><div style="padding-bottom:8px;font-weight:700">'
            "Agregar al calendario</div><div>"
            f"{''.join(links)}</div></td></tr>"
        )
    cover = ""
    if _usable_image(event.cover_url):
        cover = (
            f'<tr><td colspan="2" style="padding-bottom:16px">'
            f'<img src="{escape(_absolute(event.cover_url))}" '
            f'alt="{escape(event.title)}" width="472" style="display:block;width:100%;max-width:472px;'
            'height:auto;border:0;border-radius:8px"></td></tr>'
        )
    return (
        '<tr><td style="padding:8px 32px 24px">'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="{TINT}" '
        f'style="background:{TINT};border:1px solid {LINE};'
        'border-radius:12px"><tr><td style="padding:20px">'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{cover}'
        f'<tr>{badge}<td valign="top" style="font-family:{FONT}">{"".join(rows)}</td></tr>{calendar}'
        "</table></td></tr></table></td></tr>"
    )


def _logo(url: str | None, name: str, height: int, theme: Theme) -> str:
    """An image logo, or the name as a wordmark when there is none or it is an SVG."""
    if _usable_image(url):
        return (
            f'<img src="{escape(_absolute(url))}" alt="{escape(name)}" height="{height}" '
            f'style="display:block;height:{height}px;width:auto;border:0;margin:0 auto">'
        )
    return (
        f'<span style="font-family:{FONT};font-size:{height // 2 + 4}px;line-height:{height}px;'
        f'font-weight:800;color:{_readable(theme.secondary)}">{escape(name)}</span>'
    )


def _sender_block(sender: Sender, theme: Theme) -> str:
    """One pattern for every sender: "Enviado por" and then the club (logo, or its name as a wordmark)."""
    label = f"font-family:{FONT};font-size:14px;line-height:20px;color:{INK}"
    if sender.name:
        body = (
            f'<div style="{label};padding-bottom:8px">Enviado por</div>'
            f"{_logo(sender.logo_url, sender.name, 36, theme)}"
        )
    else:
        name = escape(theme.site_name)
        body = f'<div style="{label}">Enviado por la mesa directiva de <strong>{name}</strong></div>'
    return (
        f'<tr><td align="center" style="padding:20px 32px 24px;border-bottom:1px solid {LINE}">'
        f"{body}</td></tr>"
    )


def _footer(campaign: CampaignLike, sender: Sender, theme: Theme, unsubscribe_href: str, home: str) -> str:
    sender_line = (
        f"Enviado por {escape(sender.name)}"
        if sender.name
        else f"Enviado por la mesa directiva de {escape(theme.site_name)}"
    )
    reply = (
        f"Responde este correo para escribirle a la mesa directiva ({escape(campaign.reply_to)})."
        if campaign.reply_to
        else "Este correo no recibe respuestas."
    )
    small = f"font-family:{FONT};font-size:12px;line-height:18px;color:{MUTED}"
    link = f"color:{MUTED};text-decoration:underline"
    return (
        f'<tr><td bgcolor="{TINT}" style="background:{TINT};padding:24px 32px;{small};'
        f'border-top:1px solid {LINE}">'
        f'<p style="margin:0 0 8px;font-weight:700;color:{INK}">{sender_line}</p>'
        f'<p style="margin:0 0 8px">{escape(campaign.footer_reason)}</p>'
        f'<p style="margin:0 0 12px">{reply}</p>'
        f'<p style="margin:0"><a href="{escape(unsubscribe_href)}" style="{link}">Darte de baja</a>'
        f' · <a href="{escape(home)}" style="{link}">{escape(theme.site_name)}</a></p></td></tr>'
    )


def _render_html(
    campaign: CampaignLike,
    sender: Sender,
    theme: Theme,
    recipient_name: str,
    unsubscribe_href: str,
    event: EventCard | None,
    ics_url: str | None,
) -> str:
    home = _base()
    rows: list[str] = []
    for block in campaign.blocks:
        if isinstance(block, HeadingBlock):
            rows.append(_heading(block.text, theme))
        elif isinstance(block, ParagraphBlock):
            rows.append(_paragraph(block.text, theme))
        elif isinstance(block, ListBlock):
            rows.append(_list(block, theme))
        elif isinstance(block, ButtonBlock):
            rows.append(_button(block, theme))
        elif isinstance(block, ImageBlock):
            rows.append(_image(block))
        elif isinstance(block, DividerBlock):
            rows.append(_divider())
        elif isinstance(block, EventBlock):
            view = _event_view(block, event)
            if view is not None:
                rows.append(_event(view, theme, ics_url))
    preheader = ""
    if campaign.preheader:
        preheader = (
            '<div style="display:none;font-size:1px;line-height:1px;max-height:0;max-width:0;opacity:0;'
            f'overflow:hidden;mso-hide:all">{escape(campaign.preheader)}'
            + "&#847;&zwnj;&nbsp;" * 30
            + "</div>"
        )
    top = (
        f'<tr><td height="6" bgcolor="{theme.primary}" style="height:6px;font-size:0;line-height:0;'
        f'background:{theme.primary};border-radius:16px 16px 0 0">&nbsp;</td></tr>'
        f'<tr><td align="center" style="padding:28px 32px 20px"><a href="{escape(home)}" '
        f'style="text-decoration:none">{_logo(theme.site_logo_url, theme.site_name, 48, theme)}</a></td></tr>'
    )
    greeting = (
        f'<tr><td style="padding:24px 32px 12px;font-family:{FONT};font-size:15px;line-height:22px;'
        f'color:{MUTED}">Hola, {escape(recipient_name)}</td></tr>'
    )
    return (
        '<!doctype html><html lang="es-MX"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="color-scheme" content="light dark">'
        '<meta name="supported-color-schemes" content="light dark">'
        f"<title>{escape(campaign.subject)}</title></head>"
        f'<body style="margin:0;padding:0;background:{PAGE};color:{INK};font-family:{FONT}" bgcolor="{PAGE}">'
        f"{preheader}"
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="{PAGE}" '
        f'style="background:{PAGE}"><tr><td align="center" style="padding:24px 12px">'
        f'<table role="presentation" width="600" cellpadding="0" cellspacing="0" bgcolor="{CARD}" '
        f'style="max-width:600px;width:100%;background:{CARD};border:1px solid {LINE};border-radius:16px">'
        f"{top}{_sender_block(sender, theme)}{greeting}{''.join(rows)}"
        '<tr><td style="font-size:0;line-height:0;height:8px">&nbsp;</td></tr>'
        f"{_footer(campaign, sender, theme, unsubscribe_href, home)}"
        "</table></td></tr></table></body></html>"
    )


# ---- text ----------------------------------------------------------


def _render_text(
    campaign: CampaignLike,
    sender: Sender,
    theme: Theme,
    recipient_name: str,
    unsubscribe_href: str,
    event: EventCard | None,
    ics_url: str | None,
) -> str:
    who = (
        f"Enviado por {sender.name}" if sender.name else f"Enviado por la mesa directiva de {theme.site_name}"
    )
    parts = [f"{theme.site_name} · {_base()}", who, f"Hola, {recipient_name}"]
    for block in campaign.blocks:
        if isinstance(block, HeadingBlock):
            parts.append(_plain(block.text).upper())
        elif isinstance(block, ParagraphBlock):
            parts.append(_plain(block.text))
        elif isinstance(block, ListBlock):
            parts.append(
                "\n".join(
                    f"{number}. {_plain(item)}" if block.ordered else f"- {_plain(item)}"
                    for number, item in enumerate(block.items, 1)
                )
            )
        elif isinstance(block, ButtonBlock):
            parts.append(f"{block.label}: {block.url}")
        elif isinstance(block, ImageBlock):
            parts.append(f"[Imagen: {block.alt}] {block.link or _absolute(block.url)}")
        elif isinstance(block, DividerBlock):
            parts.append("---")
        elif isinstance(block, EventBlock):
            view = _event_view(block, event)
            if view is not None:
                _, day_line, time_line = _when(view)
                lines = [view.title, day_line, time_line]
                if view.place:
                    lines.append(f"Lugar: {view.place}")
                if view.description:
                    lines.append(_plain(view.description))
                if view.link:
                    lines.append(f"Detalles: {view.link}")
                for label, href in (
                    ("Google Calendar", view.google_url),
                    ("Outlook", view.outlook_url),
                    ("Apple / .ics", ics_url),
                ):
                    if href:
                        lines.append(f"{label}: {href}")
                parts.append("\n".join(lines))
    reply = (
        f"Responde este correo para escribirle a la mesa directiva ({campaign.reply_to})."
        if campaign.reply_to
        else "Este correo no recibe respuestas."
    )
    footer = f"-- \n{who}\n{campaign.footer_reason}\n{reply}\nDarte de baja: {unsubscribe_href}"
    return "\n\n".join(parts) + f"\n\n{footer}\n"


def render_blocks(
    campaign: CampaignLike,
    *,
    sender: Sender,
    theme: Theme,
    recipient_name: str,
    unsubscribe_href: str,
    event: EventCard | None = None,
    ics_url: str | None = None,
) -> tuple[str, str]:
    """The HTML and plain-text parts of one email; 422 when the HTML passes 100 KB (Gmail clips it)."""
    theme = Theme(
        site_name=theme.site_name,
        site_logo_url=theme.site_logo_url,
        primary=_hex(theme.primary, str(DEFAULTS["color_primary"])),
        secondary=_hex(theme.secondary, str(DEFAULTS["color_secondary"])),
        accent=_hex(theme.accent, str(DEFAULTS["color_accent"])),
    )
    html = _render_html(campaign, sender, theme, recipient_name, unsubscribe_href, event, ics_url)
    if len(html.encode()) > MAX_HTML_BYTES:
        raise AppError(422, "El correo es demasiado largo: acórtalo para que Gmail no lo recorte.")
    text = _render_text(campaign, sender, theme, recipient_name, unsubscribe_href, event, ics_url)
    return html, text
