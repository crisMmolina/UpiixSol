# Spec 003 · Email channel (Mailgun, upiixsol.com)
- Status: draft, questions answered by victor 2026-11-16 · Owner: victor (git `rvvictor`) · PROJECT principles: 1, 2, 3, 4, 5
- Widens `IDEA.md` §9 "Out: notificaciones por correo" for **manual emails sent by admins only**. Automatic notifications and password recovery by email stay out (see Out of scope).

## Problem
Today the club reaches its people through WhatsApp groups and personal mail. A superadmin has no way to write to "everyone in UpiixSol", "everyone enrolled in UpiixIA" or one specific member from the campus, even though the campus already knows who belongs where (`users`, `enrollments`, `users.academy_id`). The club owns the domain `upiixsol.com` and will send through Mailgun.

## Stories
- As a **superadmin**, I want to write one email and pick its audience (all of UpiixSol, the members of one club, one role, or specific people, campus users or outside addresses), so that the right people get it without me copying addresses by hand.
- As a **superadmin**, I want to see how many people will receive it and send myself a test first, so that I do not send a mistake to everyone.
- As an **academy admin**, I want to email the members of my own club, some of them, or a few outside addresses, so that I can announce the week's content and reach guests. [Decided · victor 2026-11-16]
- As a **member** or an outside recipient, I want to stop receiving club emails with one click, so that I control my inbox.
- As a **superadmin**, I want a history of what was sent, by whom, to how many and with what result, so that we can answer "did that email go out?".

## Acceptance criteria (EARS)
Audiences and permissions
- When a superadmin asks for the audience preview, the system shall return the number of recipients computed with a DB query, for one of: `all` (every active user), `academy` (active users enrolled in that club plus its academy_admins), `role` (`superadmin`, `academy_admin` or `member`), `individual` (campus user ids plus outside addresses typed by hand: at most 50 entries in total, at most 20 outside addresses, each a valid email).
- If an academy_admin requests `all`, `role`, another club, or an `individual` audience with a campus user who is neither enrolled in their own club (`users.academy_id`) nor a co-admin of it, the system shall respond 403 (outside addresses and the club's co-admins are allowed; decided by victor 2026-11-17); a member shall get 403 and an anonymous caller 401, on every email endpoint.
- While computing any audience, the system shall exclude inactive users, every suppressed address (unsubscribed, hard bounce or complaint; suppressions are kept per normalized email, so they cover outside addresses too) and addresses on non-deliverable domains (`MAIL_BLOCKED_DOMAINS`, default `upiixsol.dev`, the seed accounts), and count each address once.
- While a sender who is not a superadmin builds an `individual` audience, the system shall never return the email of a campus user (they pick by name or nickname); outside addresses are shown only to whoever typed them and to superadmins.

Composing and sending
- When a sender submits a subject (1–150 chars, one line) and a plain-text body (1–20 000 chars), the system shall render it into the campus email template: HTML-escaped, blank lines become paragraphs, line breaks become `<br>`, `http(s)` URLs become links (only `app/sanitize.safe_url` ones), plus the same text as the plain-text part; if a field is out of range it shall respond 422. No Markdown in v1 (no backend Markdown library; adding one is a dependency review).
- When a sender asks for a test send, the system shall send the rendered email only to the sender's own address and shall not count it as a campaign.
- When a sender creates a campaign, the system shall store it as `draft` with its frozen recipient list and count; when the sender confirms that draft by id, the system shall move it to `sending` exactly once (a repeated confirm returns the same campaign and sends nothing new), and only then call Mailgun then send in batches of at most 1 000 recipients per Mailgun call, so that each recipient sees only their own address (never the full list in To, Cc or Bcc).
- If Mailgun rejects a batch or does not answer within 10 s, the system shall mark those recipients `failed`, mark the campaign `partial` or `failed`, and show the error in Spanish without the API key or any address in the message.
- If a send would exceed the remaining quota of the Mailgun billing period (`MAIL_MONTHLY_LIMIT` minus what was sent since the period started on `MAIL_PERIOD_START_DAY`, counted in the DB), the system shall respond 422 with the remaining number before sending anything.
- If a user starts more than 5 campaigns in one hour, the system shall respond 429.
- While `MAIL_ENABLED` is false, the system shall answer 503 "El correo está desactivado" on send endpoints and send nothing; in dev and test the default backend writes the email to the log (subject and count only, no addresses) instead of calling Mailgun.

Opt-out
- If the process stops while a campaign is `sending`, its unsent recipients shall stay `pending`, and a superadmin (or the club's admin for their own campaign) shall be able to resume it, which sends only the `pending` ones.
- When a recipient opens the one-click unsubscribe link of any campaign email (also sent as `List-Unsubscribe` + `List-Unsubscribe-Post`), the system shall suppress that address without asking them to sign in; the token is random (≥ 32 bytes), stored only as a hash, single-purpose, does not reveal the user id or email, travels in the query string (`?t=`, the access log keeps only the path) and the one-click POST works form-encoded without a session (RFC 8058).
- When a signed-in user toggles "Recibir correos del club" in Mi cuenta, the system shall add or remove the suppression of their current address and apply it to the next audience computed.

History and delivery status
- When a superadmin opens the email history, the system shall list campaigns (≤ 50 per page, cursor) with sender nickname, audience, subject, date, recipient count and counts per status; an academy_admin sees only the campaigns of their own club.
- When Mailgun calls the webhook with a valid HMAC signature (signing key from env, timestamp within 5 minutes, token not reused), the system shall update that recipient's status (`delivered`, `failed`, `bounced`, `complained`); if the signature is invalid it shall respond 403 and change nothing.
- When a recipient bounces permanently or complains, the system shall suppress that address for every future campaign.

## Non-functional
- Privacy: an email address appears only in the DB, in the request to Mailgun and to superadmins; never in logs, analytics events, URLs or the response of a non-superadmin. Open and click tracking stay **off**. Recipient rows (which hold outside addresses) are purged 365 days after the campaign; suppressions are kept, since they protect the recipient.
- Volume: up to 5 000 recipients per campaign; a send of ≤ 1 000 recipients answers in < 10 s (one Mailgun call). Audience preview p95 < 300 ms on seeded data.
- Secrets: `MAILGUN_API_KEY` and `MAILGUN_WEBHOOK_SIGNING_KEY` live only in `.env` / the Render dashboard; with `ENV=prod` and `MAIL_ENABLED=true` both are required at startup.
- Deliverability: sending domain with SPF, DKIM and DMARC verified in Mailgun before the first real send (human step, runbook).
- UI in Spanish (Mexico), 1280 and 390 wide, WCAG AA, coverage target 100 % on the new code; tests never call the real Mailgun (a Fake transport).

## Out of scope
- Password recovery and email verification at sign-up (a later spec can reuse this transport).
- Automatic notifications (new event, new post, reply to my comment), scheduled sends, attachments, inline image uploads, inbound mail and replies processing, open/click tracking, a WYSIWYG editor.

## Open questions
- [x] Can an academy_admin send? Yes: their own club's members, some of them, and outside addresses · victor 2026-11-16
- [x] Sending domain: `mg.upiixsol.com`, From `UpiixSol <avisos@mg.upiixsol.com>` · victor 2026-11-16
- [x] Outside addresses: yes, for superadmin and academy_admin, at most 20 per campaign · victor 2026-11-16
- [x] `https://www.upiixsol.com` already points to the Render service: `PUBLIC_BASE_URL=https://www.upiixsol.com` · victor 2026-11-16
- [x] Unsubscribed addresses are excluded from every campaign, direct ones included (an outside address has no other way to opt out) · default, victor can change it in the plan PR
- [x] Club admins may also pick the co-admins of their own club in `individual` · victor 2026-11-17
- [x] For a club admin, the preview count of typed outside addresses may be slightly higher than the final list (suppressed outside addresses are not revealed, so the preview is no oracle) · accepted by victor 2026-11-17
- [ ] Reply-To address (draft: none, so replies go to `avisos@mg.upiixsol.com` and are dropped; or a real inbox of the board) · victor
- [ ] Mailgun plan and region (US `api.mailgun.net` or EU `api.eu.mailgun.net`); its monthly limit sets `MAIL_MONTHLY_LIMIT` and its billing day `MAIL_PERIOD_START_DAY`. Any paid plan is a spend a human authorizes · victor
