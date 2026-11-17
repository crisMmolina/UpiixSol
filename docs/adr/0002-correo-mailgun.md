# ADR 0002 · Email through Mailgun's HTTP API on `mg.upiixsol.com`, behind a transport interface
- Status: proposed · Date: 2026-11-16 · Decider: victor

## Context
Spec 003 lets superadmins and club admins email campus users and a few outside addresses. The club owns `upiixsol.com`, which already points to the Render service (`https://www.upiixsol.com`). The app runs as one free Render process with no worker and no queue (ADR 0001, UPS-030). Recipients must never see each other's address, and tests must never send real mail. Changing the sending domain later costs deliverability: a new domain starts with no reputation and needs new DNS records.

## Decision
- Provider: **Mailgun**, called through its HTTP API with `httpx` (already a runtime dependency), batch sending with `recipient-variables`, open/click tracking off.
- Sending domain: the subdomain **`mg.upiixsol.com`**, From `UpiixSol <avisos@mg.upiixsol.com>`, so the root domain's own mail and reputation stay separate. SPF and DKIM on the subdomain, DMARC on the root.
- The app talks to a `MailTransport` interface (`app/services/mailer.py`); `MailgunTransport` is one implementation, `ConsoleTransport` the dev/test default, and tests use a Fake.
- Sending runs in FastAPI `BackgroundTasks` after the campaign is committed, with recipient rows as the durable state (`pending` rows can be resumed).
- Delivery status, bounces and complaints come back through Mailgun's signed webhook; suppressions live in our DB, keyed by email.

## Alternatives
- SMTP relay (Mailgun or another): no per-recipient variables in one call and fewer per-message options; would need one SMTP message per recipient.
- Another provider (SES, Postmark, Resend): equally valid; the human chose Mailgun. The transport interface keeps the switch to a new class plus settings.
- A queue and worker (Redis/RQ, Celery): the reliable choice at scale, but Render free has no worker and the volume is hundreds per campaign.
- Sending from the root `upiixsol.com`: shorter From, but it mixes reputation with any other mail on the domain and touches its existing MX/SPF.

## Consequences
Easy: tests without network, switching provider or adding password-recovery mail later on the same transport. Hard: a restart in the middle of a campaign needs a manual "Reanudar" (no worker); the webhook replay guard is in memory (one process, as the rate limiter). Reversible: `MAIL_ENABLED=false` stops all sending at once; migration 0009 is additive. Changing the sending domain means new DNS records and warming the new domain up.
