# Plan 004 · Rich emails
Spec: `docs/specs/004-correo-bonito/spec.md` · builds on plan 003 and ADR 0002 · Human owner: victor

## Design
```
Composer (blocks, event picker, image upload, Reply-To)
   │ debounce 400 ms
   ├─ POST /api/mail/preview ──► mail_blocks.validate ─► mail_render.render(campaign-like) ─► {html, text}
   │                                                     (iframe srcdoc, sandbox="", 600 / 375 px)
   ├─ POST /api/mail/images  ──► media.save_email_image  ─► /media/mail/<uuid>.jpg|png (public)
   └─ POST /api/mail/campaigns (+ /send) ─► store blocks JSON ─► send: mail_render + evento.ics attachment
Inbox ─► "Apple / .ics" ─► GET /api/mail/ics/<token>.ics (public, random token, 404 otherwise)
```
- **Blocks** (`app/services/mail_blocks.py`): a Pydantic discriminated union on `kind`; validated input is stored as JSON on the campaign and rendered at send time. The event block stores either `event_id` or the typed fields; at send time an `event_id` is resolved from the DB.
- **Renderer** (`app/services/mail_render.py`): replaces the plain-text layout of `mail_template.py` for block campaigns (the old function stays for legacy `body` campaigns). Hand-written table layout with inline styles (no CSS inliner dependency). Inline formatting by a small escape-first parser (`**`, `*`, `[t](url)`), never raw HTML. Header = UpiixSol site logo always, then the sender block ("Enviado por <club>" with the club logo or name and accent color). Theme accents = sender club's `color_primary/secondary/accent`, else `SiteSettings`; an SVG club logo falls back to the club name as a wordmark. Typed event times without an offset are America/Mexico_City.
- **Calendar** (`app/services/mail_ics.py`): RFC 5545 writer (CRLF, 75-octet folding, escaping of `,;\\` and newlines, `UID` from the campaign token, `DTSTAMP`, UTC times); Google `calendar.google.com/calendar/render?action=TEMPLATE&text=&dates=YYYYMMDDTHHMMSSZ/…&details=&location=`; Outlook `outlook.live.com/calendar/0/deeplink/compose?subject=&startdt=&enddt=&body=&location=`. The transport gains attachments (Mailgun `attachment` part).
- **Why blocks and a server renderer:** one renderer for preview and send means "what you see is what they get"; blocks keep the HTML safe and predictable across Gmail/Outlook/Apple, which a free HTML editor would not.
- **Why remove the test send:** the human asked for it; the live preview replaces it.

## Data and migrations
Migration `0010_mail_blocks` (down_revision `0009`), expand-only on `mail_campaigns`: `content` JSON nullable (blocks, version), `sender_academy_id` FK academies SET NULL nullable (NULL = UpiixSol), `preheader` String(140) nullable, `reply_to` String(254) nullable, `ics_token` String(43) nullable unique. Legacy rows keep `body` and `content=NULL`. Round-trip runs only against a temp SQLite (`DATABASE_URL=sqlite:////tmp/…`) and CI's localhost Postgres (UPS-084 guard).

## Contracts
| Method · path | Who | Notes |
|---|---|---|
| `POST /api/mail/preview` | superadmin; academy_admin (own club audience) | `{subject, preheader?, reply_to?, blocks, audience}` → `{html, text}`; same validation as create |
| `POST /api/mail/campaigns` | as today | body gains `preheader?`, `reply_to?`, `blocks` (`body` stays accepted: legacy campaigns and clients keep working) |
| `POST /api/mail/images` | superadmin, academy_admin | multipart `file` → `{url}`; rate-limited per user |
| `GET /api/mail/ics/{token}.ics` | public | `text/calendar; charset=utf-8`; 404 on unknown token |
| `POST /api/mail/test` | — | removed (matrix row and its tests go away with `uak allow --tests` by a human) |
| `GET /api/events?…` | as today | the composer's event picker reuses it |

`MailMessage` (UPS-072) gains `attachments: list[(filename, content_type, bytes)]`, `reply_to: str | None` and `from_name: str | None` (display name only; the address stays `MAIL_FROM`'s); `MailgunTransport` sends them (`attachment`, `h:Reply-To`). Web types mirror `Block`, `PreviewOut`.

## Threat model (STRIDE)
| Threat | Vector | Mitigation | Test |
|---|---|---|---|
| Tampering / XSS in mail | HTML or `javascript:` in a paragraph, list, button or image | escape-first renderer, links through `safe_url`, no raw HTML block | test_paragraph_html_is_escaped, test_javascript_link_is_dropped |
| Tampering | Header injection through `reply_to` or subject | `reply_to` must be one valid address (no CR/LF), subject one line | test_reply_to_with_newline_is_422 |
| Information disclosure | `.ics` endpoint leaks other campaigns | random 32-byte token per campaign, 404 otherwise, no listing | test_unknown_ics_token_is_404 |
| Information disclosure | Preview iframe runs scripts in the admin's session | `srcdoc` with `sandbox=""` (no scripts, no same-origin) | e2e test_preview_iframe_is_sandboxed |
| Spoofing | Club admin sends as another club or as the board | sender of an academy_admin forced from `users.academy_id`; superadmin only picks active clubs; From address never changes | test_academy_admin_sender_is_always_own_club |
| Elevation of privilege | Club admin references another club's event | event scope from the DB row | test_academy_admin_cannot_reference_other_club_event |
| Denial of service | Huge uploads or 30 heavy images | 5 MB per file, real type, ≤ 1200 px re-encode, ≤ 30 blocks, HTML ≤ 100 KB | test_email_image_too_large_is_413, test_html_size_cap |

## Observability
Same as plan 003: logs carry campaign id and counts, never addresses or content.

## Rollout and rollback
Ships behind the existing `MAIL_ENABLED`. Legacy campaigns keep working. Rollback = revert the web composer; the API keeps accepting blocks; migration 0010 is additive.

## Cost
None beyond plan 003 (attachments add a few KB per email).

## Tasks
UPS-085 (contract) · UPS-086 (renderer) · UPS-087 (calendar) · UPS-088 (email images) · UPS-089 (API: blocks, preview, Reply-To, remove test send) · UPS-090 (web: block composer + live preview) · UPS-091 (web: event picker, image upload, Reply-To).
