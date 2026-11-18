# Plan 003 · Email channel (Mailgun, upiixsol.com)
Spec: `docs/specs/003-correo/spec.md` · ADR: `docs/adr/0002-correo-mailgun.md` · Human owner: victor

## Design
```
Composer (superadmin tab / club panel tab)
  │ POST /api/mail/audience/preview ──► mail_audience.resolve()  (DB: users, enrollments, suppressions)
  │ POST /api/mail/test             ──► mail_template.render() ──► transport.send_batch([me])
  │ POST /api/mail/campaigns        ──► draft + frozen mail_recipients (pending, unsubscribe token hash)
  │ POST /api/mail/campaigns/{id}/send ─► draft→sending (once) ─► BackgroundTasks: batches of ≤1000
  │                                                           └► MailgunTransport (httpx, 10 s timeout)
Mailgun ──► POST /api/mail/webhooks/mailgun (HMAC) ──► recipient status, suppress bounces/complaints
Inbox   ──► /baja?t=…  (SPA) or one-click POST /api/mail/unsubscribe?t=…  ──► mail_suppressions
```
- **Transport interface** (`app/services/mailer.py`): `MailTransport.send_batch(message, recipients) -> BatchResult`. Implementations: `ConsoleTransport` (dev/test default: logs subject and count only), `MailgunTransport` (`app/services/mailgun.py`), and a `FakeMailTransport` defined in the tests (records calls, can fail on demand). `get_mail_transport()` is a FastAPI dependency, so tests override it; nothing in CI reaches Mailgun.
- **Batch sending:** one Mailgun call per ≤ 1 000 recipients with `recipient-variables` (`%recipient.name%`, `%recipient.unsubscribe_url%`), so each recipient sees only their own address. `o:tracking=no`, `o:testmode=yes` when `MAILGUN_TEST_MODE=true`, `v:campaign_id` for the webhook. Whether Mailgun substitutes recipient variables inside a custom `h:List-Unsubscribe` header is confirmed by the spike (UPS-071); if not, the fallback is one call per recipient below 100 recipients and Mailgun's own `%unsubscribe_url%` synced through the webhook above that.
- **Sending in the background:** `POST …/send` flips `draft → sending` with a conditional UPDATE (`WHERE status='draft'`), commits, answers 202, and a `BackgroundTasks` job sends the batches in order, committing each batch's result. A crash leaves `pending` rows; `POST …/resume` sends only those. Why not a queue/worker: Render free has no worker and the club's volume (hundreds) fits one process; why not synchronous: 5 batches × 10 s worst case would hold the request open past what a browser tolerates.
- **Template** (`app/services/mail_template.py`): one HTML layout with inline styles owned by the server (site name and logo from `SiteSettings`, absolute URLs from `PUBLIC_BASE_URL`), the escaped body inside, footer with "Darte de baja" and why you got it ("Recibes este correo porque eres parte de UpiixSol" / "…de <club>" / "…porque <nickname> te lo envió"). nh3 is not run over the layout (it would strip the styles); the user part is escaped, never trusted.
- **Alternatives considered:** SMTP through Mailgun (simpler client, but no batch variables and no per-call options); a generic multi-provider library (one more dependency for one provider). See ADR 0002.

## Data and migrations
Migration `0009_mail` (down_revision `0008_unique_nickname`, UPS-070), expand-only: three new tables, nothing existing changes, downgrade drops them. Round-trips on SQLite and PostgreSQL 16.

| Table | Columns | Notes |
|---|---|---|
| `mail_campaigns` | id, sender_id → users SET NULL, academy_id → academies SET NULL (club scope of the sender/audience), audience_kind (`all`/`academy`/`role`/`individual`), audience_params JSON (academy_id, role, user_ids; never addresses), subject, body, status (`draft`/`sending`/`sent`/`partial`/`failed`), recipient_count, counts_snapshot JSON nullable (counts per status kept when the recipient rows are purged), created_at, sent_at, finished_at | index (sender_id), (academy_id, created_at) |
| `mail_recipients` | id, campaign_id → CASCADE, user_id → users SET NULL nullable, email (254, normalized lowercase), name, status (`pending`/`accepted`/`delivered`/`failed`/`bounced`/`complained`), provider_message_id, error_code (short, no PII), unsubscribe_token_hash (64, unique), updated_at | unique (campaign_id, email); index (status), (created_at) for quota and purge |
| `mail_suppressions` | email PK (normalized), reason (`unsubscribed`/`bounced`/`complained`), campaign_id nullable, created_at | covers campus users and outside addresses; Mi cuenta toggle adds/removes the row of the current address |

Quota = rows of `mail_recipients` with status ≠ `pending` and `updated_at` since the start of the current Mailgun billing period (UTC, starts on `MAIL_PERIOD_START_DAY`) — a DB count, never an estimate. Purge (UPS-081): recipient rows of campaigns older than 365 days are deleted, keeping the campaign's counts.

## Contracts
All under `/api/mail`, JSON, errors `{"error": {...}}`, lists = cursor pages ≤ 50. Schemas live next to their service (as `app/services/site.py` does), so `app/schemas/` stays untouched; `web/src/lib/types.ts` mirrors them.

| Method · path | Who | Body / answer |
|---|---|---|
| `GET /status` | superadmin, academy_admin | `{enabled, monthly_limit, sent_this_period, remaining, period_start, period_end}` |
| `POST /audience/preview` | superadmin; academy_admin own club | `Audience` → `{count, excluded: {inactive, suppressed, blocked_domain}}` |
| `GET /recipients?q=` | superadmin (all users); academy_admin (own club's enrollees and co-admins) | page of `{id, full_name, nickname, avatar_url}`; email only for superadmin |
| `POST /test` | superadmin, academy_admin | `{subject, body}` → 202, sent to the caller only |
| `POST /campaigns` | same as preview | `{subject, body, audience}` → 201 `Campaign` (`draft`) |
| `POST /campaigns/{id}/send` · `/resume` | the campaign's sender or superadmin | → 202 `Campaign`; idempotent |
| `GET /campaigns` · `/campaigns/{id}` | superadmin all; academy_admin own club | `Campaign{id, subject, audience, sender: PublicUser, status, recipient_count, counts_by_status, created_at, sent_at}` |
| `GET /preferences` · `PUT /preferences` | any signed-in user | `{receive_club_email: bool}` |
| `POST /unsubscribe?t=` | public (token) | form or JSON; 200 even for an unknown token (no oracle) |
| `POST /webhooks/mailgun` | public (HMAC) | Mailgun event JSON; 403 on bad signature |

`Audience = {kind: "all"} | {kind: "academy", academy_id} | {kind: "role", role} | {kind: "individual", user_ids: int[], emails: str[]}` (≤ 50 entries, ≤ 20 emails).
Settings (`app/config.py`, `.env.example`): `MAIL_ENABLED` (false), `MAIL_BACKEND` (`console`|`mailgun`), `MAILGUN_API_KEY`, `MAILGUN_DOMAIN` (`mg.upiixsol.com`), `MAILGUN_API_BASE` (`https://api.mailgun.net`, EU: `https://api.eu.mailgun.net`), `MAILGUN_WEBHOOK_SIGNING_KEY`, `MAILGUN_TEST_MODE` (false), `MAIL_FROM` (`UpiixSol <avisos@mg.upiixsol.com>`), `MAIL_REPLY_TO` (empty), `MAIL_MONTHLY_LIMIT` (3000), `MAIL_PERIOD_START_DAY` (1), `MAIL_BLOCKED_DOMAINS` (`upiixsol.dev`), `PUBLIC_BASE_URL` (`https://www.upiixsol.com`). With `ENV=prod`, `MAIL_ENABLED=true` and `MAIL_BACKEND=mailgun`, the API key, domain and signing key are required at startup.
Consumers: superadmin panel and club panel (new "Correos" tab), Mi cuenta (toggle), new SPA route `/baja`. Permission matrix: every new write endpoint gets a row (OWN rules use `{kind: "academy", academy_id: world.academy_id}`); payload-dependent 403s are tested in `test_mail_*`.

## Threat model (STRIDE)
| Threat | Vector | Mitigation | Test |
|---|---|---|---|
| Spoofing | Forged Mailgun webhook marks mail delivered or suppresses addresses | HMAC-SHA256(signing key, timestamp+token) with `hmac.compare_digest`, timestamp ≤ 5 min, token seen once (in-memory, one process as ADR 0001) | test_webhook_rejects_bad_signature, _old_timestamp, _replayed_token |
| Spoofing | Mail from `mg.upiixsol.com` faked by others | SPF + DKIM on the subdomain, DMARC on `upiixsol.com` (runbook, human step) | runbook checklist (UPS-080) |
| Tampering | Sender injects headers or HTML through subject/body | Subject one line (no CR/LF), body HTML-escaped, links only via `safe_url`, From/Reply-To only from settings | test_subject_with_newline_is_422, test_body_html_is_escaped |
| Repudiation | "I never sent that" | Campaign stores sender, audience, subject, body, timestamps; history visible to superadmins | test_history_shows_sender_and_counts |
| Information disclosure | Recipient list leaks (To/Cc), admins harvest member emails, addresses in logs | Batch with recipient-variables (one To each); search returns no emails to academy_admins; logs carry ids and counts only; recipient rows purged at 365 days | test_each_recipient_gets_only_their_address, test_recipient_search_hides_email_from_academy_admin, test_console_transport_logs_no_addresses, test_purge_* |
| Information disclosure | Unsubscribe endpoint as an oracle (which addresses exist) | Same 200 answer for unknown tokens; token random, hashed, in the query string | test_unknown_token_answers_like_a_valid_one |
| Denial of service | Spam to outside addresses / burning the Mailgun quota | ≤ 20 outside addresses per campaign, 5 campaigns per hour per user, period quota from the DB, `MAIL_ENABLED` kill switch, history visible to superadmins | test_rate_limit_6th_campaign_is_429, test_monthly_quota_exceeded_is_422_before_sending |
| Denial of service | Double click / retried confirm sends twice | `draft → sending` conditional update; resume sends only `pending` | test_confirm_twice_sends_once, test_resume_sends_only_pending |
| Elevation of privilege | academy_admin mails all users, another club or non-members | Audience scope checked in the service from DB rows (`users.academy_id`), never from the body | test_academy_admin_cannot_mail_all / _role / _other_club / _non_enrolled_user |

## Observability
- Logs (JSON, no PII): `mail.campaign` with campaign id, sender id, audience kind, recipient count, batch number, status, Mailgun HTTP status; never addresses, subject or body. The API key never appears (httpx auth, error messages scrubbed).
- Analytics (UPS-037): `mail.campaign_sent` with the count only.
- In-app: history counts per status; a campaign stuck in `sending` > 15 min shows "Interrumpido · Reanudar".
- Alert: none in v1 (no monitoring stack); the runbook says to check Mailgun's dashboard for bounce rate > 5 %.

## Rollout and rollback
1. Merge with `MAIL_ENABLED=false` (default): the tab shows "El correo está desactivado".
2. victor creates the Mailgun account, adds `mg.upiixsol.com`, DNS records, webhook URL `https://www.upiixsol.com/api/mail/webhooks/mailgun`, and the Render env vars (runbook UPS-080).
3. `MAILGUN_TEST_MODE=true` + `MAIL_ENABLED=true`: send to the board only, check Mailgun logs.
4. Test mode off; first real campaign to the superadmins (`role`), then one club, then `all`.
Promotion criterion: delivered ≥ 95 % and no complaint in the first two campaigns. Rollback: `MAIL_ENABLED=false` (no redeploy of code; migration 0009 is additive and can stay).

## Cost
Infra: none (same Render service, three small tables in Neon). Mailgun: depends on the plan victor picks (unverified here; check the current pricing page). The Free plan caps 3,000 emails per billing period, which `MAIL_MONTHLY_LIMIT` enforces. Any paid plan is a spend a human authorizes.

## Tasks
UPS-071 (spike) · UPS-072 (contract) · UPS-073 (Mailgun transport) · UPS-074 (audience) · UPS-075 (campaigns) · UPS-076 (unsubscribe + preference) · UPS-077 (webhook) · UPS-078 (web: superadmin tab) · UPS-079 (web: club tab, Mi cuenta, /baja) · UPS-080 (runbook) · UPS-081 (retention purge). Each starts with its `Tests:`; `uak graph` and `uak lint` pass.
