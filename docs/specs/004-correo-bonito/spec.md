# Spec 004 · Rich emails: block composer, live preview, events with calendar, images, Reply-To
- Status: draft, decisions by victor 2026-11-17 · Owner: victor (git `rvvictor`) · PROJECT principles: 1, 2, 4, 5, 6
- Builds on spec 003 (`docs/specs/003-correo/`), already integrated (UPS-071…081). Replaces its "plain-text body, no Markdown, no image uploads, no attachments" limits for campaign emails only.

## Problem
The first real campaign (2026-11-17) arrived with the logo and plain paragraphs: "El día de mañana será la primera clase… Salón 205… 3 pm a 5 pm… Trae tu laptop". It works, but it looks bare, the event details are loose text, there is no way to send people to the campus or save the event in their calendar, the sender cannot see what the email will look like before sending, and a reply goes to `avisos@mg.upiixsol.com`, where nobody reads it.

## Stories
- As a **superadmin** or **club admin**, I want to build an email from blocks (title, paragraph, list, button, event, image, divider) with the club's look, so that announcements look designed without knowing HTML.
- As a sender, I want to see the exact email, on desktop and phone widths, while I build it, so that I send it with confidence (this replaces the "Enviarme una prueba" button, which is removed).
- As a sender, I want to pick an event from the campus calendar or type one, so that recipients get a card with date, time and place plus "Agregar a Google Calendar", "Outlook" and "Apple / .ics".
- As a sender, I want buttons like "Ir al campus" or "Ver el club", and to upload a cover or inline images.
- As a recipient, I want my reply to reach a real person of the board.

## Acceptance criteria (EARS)
Content and rendering
- When a sender submits a campaign, the system shall accept `subject` (1–150, one line), optional `preheader` (≤ 140, the inbox preview text), optional `reply_to` (one valid email) and `blocks`: 1–30 blocks of kinds `heading`, `paragraph`, `list`, `button`, `event`, `image`, `divider`, at most 1 `event` block; any other shape is 422 with a Spanish message.
- While rendering, the system shall produce one HTML part and one plain-text part from the same blocks with one server renderer (used by preview and by sending): table layout ≤ 600 px, inline styles, the logo of the audience's club (or the site's) at the top, accent colors from that club (or the site), a hidden preheader, buttons that work without images (cell background), a design that stays readable when Gmail dark mode inverts colors, alt text on every image, absolute `https://www.upiixsol.com` URLs.
- In `paragraph` and `list` items, the system shall support `**negritas**`, `*cursivas*` and `[texto](https://…)`, escape everything else, and accept only links that `app/sanitize.safe_url` accepts; raw HTML is never passed through.
- `button` blocks have a label (≤ 40) and an http(s) URL; the composer offers presets "Ir al campus" (`/`) and "Ver el club" (`/a/<slug>`).

Events and calendar
- When an `event` block references a campus event by id, the system shall read title, description, place, link, start, end and cover from the DB at send time; an academy_admin may only reference global events or events of their own club (403 otherwise).
- When an `event` block is typed by hand, the system shall require title (≤ 120), start and end (end > start), and accept place, description and link.
- The rendered event card shall show weekday, date and time in `America/Mexico_City` (UTC-6) and three links: Google Calendar (template URL), Outlook (deeplink) and "Apple / .ics" pointing to a public `.ics` URL with a random per-campaign token; the same `.ics` (RFC 5545, `METHOD:PUBLISH`, UTC times) is attached to the email as `evento.ics`.
- An unknown or malformed `.ics` token answers 404 with no detail.

Images
- When a sender uploads an email image (png, jpg or webp, ≤ 5 MB, real type checked), the system shall store a JPEG or PNG copy (≤ 1200 px wide) under `/media/mail/…`, publicly readable without a session, and return its absolute URL; SVG is refused (email clients do not show it). Event covers and the site/club logo used in emails get the same PNG/JPEG copy, because Outlook desktop does not show WebP.

Preview, test send and Reply-To
- When a sender asks for a preview, the system shall return the HTML and text the recipient would get (with a sample name and a non-working unsubscribe link), computed by the same renderer; the composer shows it in a sandboxed iframe with desktop (600 px) and phone (375 px) toggles and updates it while typing (debounced).
- The test send (`POST /api/mail/test` and the "Enviarme una prueba" button) shall no longer exist (decision by victor 2026-11-17).
- When a campaign has `reply_to`, the email shall carry `Reply-To` with it; otherwise `MAIL_REPLY_TO` from settings; the footer says "Responde este correo para escribirle a la mesa directiva" when there is a Reply-To and "Este correo no recibe respuestas" when there is none.

Compatibility
- Campaigns created before this spec (plain `body`) keep rendering and showing in history; resume of a `sending` campaign renders with the version it was created with.

## Non-functional
- The email renders correctly in Gmail (web, Android, iOS, dark mode), Apple Mail and Outlook (web and desktop): checked with the screenshots of the e2e preview at 600 and 375 px and one real send per client listed in the runbook.
- HTML ≤ 100 KB per email (Gmail clips longer messages).
- Preview p95 < 300 ms; the composer stays usable at 390 px wide; Spanish (Mexico); WCAG AA in the composer.
- No new backend dependency (own block renderer, own `.ics` writer); frontend dependencies only if the dependency review in `.uak/docs/SECURITY.md` passes.

## Out of scope
- A WYSIWYG/free HTML editor, saved reusable templates, scheduled sends, open/click tracking, RSVP or attendance tracking from the email, more than one event per email.

## Open questions
- [x] Content model: blocks · victor 2026-11-17
- [x] Event: from the campus calendar or typed by hand · victor 2026-11-17
- [x] Replies go to a real inbox of the board (Reply-To) · victor 2026-11-17
- [x] Images: cover and inline uploads · victor 2026-11-17
- [x] Remove the test send · victor 2026-11-17
- [ ] Which inbox is the default `MAIL_REPLY_TO` (victor sets it in Render; never committed) · victor
