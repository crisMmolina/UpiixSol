"""Campus email template (UPS-075, spec 003 §Composing and sending, plan §Design · Template).

    html, text = render(subject, body, footer_reason(kind, site_name=...), site=get_site(db))

The layout and its inline styles belong to the server; only the sender's subject and body come from the
request, and they are HTML-escaped, never trusted (nh3 is not run over the layout: it would strip the
styles). Blank lines start paragraphs, line breaks become `<br>`, and `http(s)` URLs become links only when
`app.sanitize.safe_url` accepts them. Brand (name, logo) comes from `SiteSettings`; every URL is absolute,
built from `PUBLIC_BASE_URL`.

Unsubscribe link: Mailgun only receives the `name` and `unsubscribe_url` recipient variables (UPS-073), and
`unsubscribe_url` is the one-click API URL (`/api/mail/unsubscribe?t=…`, contract #464). The footer links to
that same variable; UPS-076 turns a GET on it into a redirect to the `/baja?t=…` page (decision recorded with
`uak decision`), so a click never unsubscribes by itself and prefetchers change nothing.
"""

import re
from html import escape

from app.config import get_settings
from app.sanitize import safe_url
from app.services.site import DEFAULTS, SiteOut

UNSUBSCRIBE_HREF = "%recipient.unsubscribe_url%"
_URL = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
_TRAILING = ".,;:!?)]}'\""  # punctuation that ends a sentence, not the URL
_PARAGRAPHS = re.compile(r"\n[ \t]*\n+")


def footer_reason(
    kind: str, *, site_name: str, club_name: str | None = None, sender_nickname: str | None = None
) -> str:
    """Why this person got the email (plan §Design): the club, the person who sent it, or the campus."""
    if kind == "academy" and club_name:
        return f"Recibes este correo porque eres parte de {club_name}."
    if kind == "individual" and sender_nickname:
        return f"Recibes este correo porque {sender_nickname} te lo envió."
    return f"Recibes este correo porque eres parte de {site_name}."


def _absolute(url: str) -> str:
    if re.match(r"https?://", url, re.IGNORECASE):
        return url
    return f"{_base()}/{url.lstrip('/')}"


def _base() -> str:
    return get_settings().public_base_url.rstrip("/")


def _linkify(line: str) -> str:
    """Escape one line; URLs accepted by `safe_url` become links, anything else stays plain text."""
    out: list[str] = []
    last = 0
    for match in _URL.finditer(line):
        url = match.group(0).rstrip(_TRAILING)
        end = match.start() + len(url)
        out.append(escape(line[last : match.start()]))
        try:
            href = safe_url(url)
        except ValueError:
            out.append(escape(url))
        else:
            out.append(f'<a href="{escape(href)}" style="color:#04944F">{escape(url)}</a>')
        last = end
    out.append(escape(line[last:]))
    return "".join(out)


def _body_html(body: str) -> str:
    paragraphs = [p for p in _PARAGRAPHS.split(body.replace("\r\n", "\n").strip()) if p.strip()]
    return "".join(
        '<p style="margin:0 0 16px;line-height:1.5">'
        + "<br>".join(_linkify(line) for line in paragraph.split("\n"))
        + "</p>"
        for paragraph in paragraphs
    )


def render(subject: str, body: str, footer: str, *, site: SiteOut | None = None) -> tuple[str, str]:
    """The HTML and plain-text parts of one email. `footer` is the reason line (`footer_reason`)."""
    name = site.name if site else str(DEFAULTS["name"])
    logo = site.logo_url if site else DEFAULTS["logo_url"]
    home = _base()
    brand = (
        f'<img src="{escape(_absolute(logo))}" alt="{escape(name)}" height="40" style="height:40px;border:0">'
        if logo
        else f'<strong style="font-size:20px;color:#04944F">{escape(name)}</strong>'
    )
    html = (
        '<!doctype html><html lang="es-MX"><head><meta charset="utf-8">'
        f"<title>{escape(subject)}</title></head>"
        '<body style="margin:0;padding:0;background:#f4f5f4;'
        'font-family:Arial,Helvetica,sans-serif;color:#1d1d1b">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">'
        '<table role="presentation" width="600" cellpadding="0" cellspacing="0" '
        'style="max-width:600px;width:100%;background:#ffffff;margin:24px 0">'
        f'<tr><td style="padding:24px"><a href="{escape(home)}">{brand}</a></td></tr>'
        f'<tr><td style="padding:0 24px 8px;font-size:16px">{_body_html(body)}</td></tr>'
        '<tr><td style="padding:16px 24px;border-top:1px solid #e3e5e3;font-size:12px;color:#5c605c">'
        f'<p style="margin:0 0 8px">{escape(footer)}</p>'
        f'<p style="margin:0"><a href="{UNSUBSCRIBE_HREF}" style="color:#5c605c">Darte de baja</a>'
        f' · <a href="{escape(home)}" style="color:#5c605c">{escape(name)}</a></p>'
        "</td></tr></table></td></tr></table></body></html>"
    )
    text = f"{body.strip()}\n\n-- \n{name} · {home}\n{footer}\nDarte de baja: {UNSUBSCRIBE_HREF}\n"
    return html, text
