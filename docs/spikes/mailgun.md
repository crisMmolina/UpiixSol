# Spike · Mailgun batch sending, unsubscribe headers and webhook signature (UPS-071)

Result: **docs-only**. No Mailgun call was made: the key lives in `.env`, which agents cannot read (guard), and no mail setting exists in `app/config.py` yet (UPS-072). Every answer below comes from Mailgun's documentation, read on **2026-11-17**. Anything the docs do not state is marked **unverified** with the check to run. Fixtures: `app/tests/fixtures/mailgun/` (see its `README.md`).

Consumers: UPS-073 (transport), UPS-077 (webhook). Plan: `docs/specs/003-correo/plan.md` §Design. ADR: `docs/adr/0002-correo-mailgun.md`.

## Summary of decisions
| Question | Answer | Status |
|---|---|---|
| Endpoint and auth | `POST {base}/v3/{domain}/messages`, HTTP Basic `api:<key>` | documented |
| Max recipients per call | 1 000 (`to` repeated + `recipient-variables`) | documented |
| `%recipient.*%` inside `h:List-Unsubscribe` | not stated anywhere | **unverified** → use the plan fallback until checked |
| `List-Unsubscribe-Post` | plain `h:` header, value `List-Unsubscribe=One-Click` (RFC 8058) | header mechanism documented; Mailgun's treatment **unverified** |
| Webhook body | `{"signature": {...}, "event-data": {...}}` | signature wrapper documented; see conflict below |
| Signature | hex HMAC-SHA256(signing key, `timestamp + token`) | documented |

## 1. Messages endpoint and auth (US and EU)
- `POST /v3/{domain_name}/messages`. Source: <https://documentation.mailgun.com/docs/mailgun/api-reference/send/mailgun/messages/post-v3--domain-name--messages> (2026-11-17). The reference says `Security: basicAuth`; the curl examples in <https://documentation.mailgun.com/docs/mailgun/user-manual/sending-messages/batch-sending> use `--user 'api:YOUR_API_KEY'`, so the user is the literal `api` and the password the API key.
- Base URLs: US `https://api.mailgun.net`, EU `https://api.eu.mailgun.net`. The US URL is in the curl examples; the EU host appears in <https://documentation.mailgun.com/docs/mailgun/user-manual/webhooks/securing-webhooks> (TLS-cert download links). The sending pages only say to use the base URL of the region where the domain lives. The domain `mg.upiixsol.com` is created in one region: `MAILGUN_API_BASE` must match it (a wrong region is **unverified** as to its exact error; expect 401/404).
- Body: `multipart/form-data` or `application/x-www-form-urlencoded`. Send options (`o:`, `h:`, `v:`, `t:`) are capped at **16 KB in total**; the message at 25 MB.
- Responses (field names from the reference; it renders no example bodies):
  - 200: `{"id": "<…>", "message": "Queued. Thank you."}`. The reference documents `id` and `message`; the "Queued. Thank you." text is **unverified** (reconstructed fixture).
  - 400: `{"message": "…"}`. 401: no schema in the reference; Mailgun is known to answer plain text `Forbidden` (**unverified**). 429 and 500 carry `{"message"}`.
  - UPS-073 must treat 401/403 as a configuration error (no retry, no key in the message), 429 and 5xx as retryable, other 4xx as a permanent batch error.

## 2. Maximum recipients per call
- **1 000** recipients per batch: "The maximum number of recipients allowed for batch is 1,000" (batch-sending page) and "Maximum 1,000 recipients per batch" under `recipient-variables` in the reference. Batch recipients are repeated `to` parameters. Duplicate addresses are ignored by Mailgun.
- Without `recipient-variables` every recipient sees all addresses in `To`: the call must always include them (batch-sending page, warning). The keys of the JSON must be the plain addresses (no display name), the same strings as in `to`.
- Plan §Design (batches of ≤ 1 000) holds. Use fewer per call if the 16 KB limit is near: `recipient-variables` counts as a form field, not an option, but a large per-recipient JSON should be checked with a 1 000-recipient test-mode call (**unverified**).

## 3. `%recipient.*%` inside a custom `h:List-Unsubscribe`  — **unverified**
- Syntax documented: `recipient-variables='{"a@example.com": {"name": "Alice"}}'`, referenced as `%recipient.name%`.
- Locations shown working in the docs: subject, text body, and `To:` (`To: %recipient%`). The batch-sending page says "Mailgun recommends only placing recipient variables in one of the supported locations described" and does **not** list custom headers. Nothing in the messages reference, the batch page or the tracking pages says that `h:` headers are substituted.
- `o:testmode` messages are accepted but not delivered ("Messages are processed normally but not actually delivered"), so test mode cannot show the final header either way, except through the stored message (the `accepted` event carries a `storage.url`), which needs the key.
- **Decision:** treat it as **not supported** until proven. Plan §Design fallback applies: one call per recipient (the unsubscribe URL put straight into `h:List-Unsubscribe`) up to the threshold the plan sets, and Mailgun's own `%unsubscribe_url%` above it, synced to `mail_suppressions` through the `unsubscribed` webhook. UPS-073 should build the headers in one function so the batch variant can be switched on by flipping a single branch.
- **How to verify later (victor, key in `.env`, ≤ 5 min):** send one `o:testmode=yes` batch of two `@example.com` recipients with `h:List-Unsubscribe=<https://www.upiixsol.com/baja?t=%recipient.unsubscribe_token%>` and distinct tokens in `recipient-variables`; fetch the message through the `storage.url` of the `accepted` event (Basic auth, same key) and compare the header per recipient. If the two headers differ and carry the tokens, batching is confirmed. Append the result to this file.

## 4. `List-Unsubscribe-Post`
- Mailgun has no dedicated parameter: any header is added with `h:<Name>` ("Adds custom headers to the email. Use 'h:' prefix followed by header name and value", reference). So: `h:List-Unsubscribe=<https://www.upiixsol.com/api/mail/unsubscribe?t=TOKEN>, <mailto:…>` and `h:List-Unsubscribe-Post=List-Unsubscribe=One-Click` (value fixed by RFC 8058 §3.1, <https://www.rfc-editor.org/rfc/rfc8058>). The `mailto:` part is optional; the `https` URL is required for one-click.
- Not documented by Mailgun (**unverified**): whether it overrides or duplicates an automatic header when domain-level unsubscribe tracking is on, and whether it signs the header with DKIM (RFC 8058 requires both headers to be DKIM-signed; check the `DKIM-Signature` `h=` list of a stored message).
- Mailgun's own mechanism is `%unsubscribe_url%`, `%tag_unsubscribe_url%`, `%mailing_list_unsubscribe_url%` in the body, requires the Unsubscribe feature on in domain settings, and fires the `unsubscribed` webhook (<https://documentation.mailgun.com/docs/mailgun/user-manual/tracking-messages/tracking-unsubscribes>). The docs do not say whether a mail client's one-click POST to our own URL is reported to Mailgun: it is not, so our endpoint writes `mail_suppressions` itself.

## 5. `o:tracking`, `v:` and events
- `o:tracking`: "Toggles both click and open tracking on a per-message basis"; values `yes`, `no`, `true`, `false`, `htmlonly`. Also `o:tracking-clicks` (overrides the domain setting) and `o:tracking-opens`. ADR 0002 sends **`o:tracking=no`**.
- `o:testmode`: the reference lists the enum `yes`; the test-mode page also accepts `true`. The page warns "You are charged for messages sent in test mode!" (<https://documentation.mailgun.com/docs/mailgun/user-manual/sending-messages/test-mode>): `MAILGUN_TEST_MODE=true` is free of recipients, not of quota. Always send `yes`.
- `v:my-var`: "treated as metadata and included in events/webhooks", "visible in the delivered email's `X-Mailgun-Variables` header", "anything over 4KB will be truncated". So `v:campaign_id=42` is readable by the recipient: **never put personal data or tokens in `v:`**. Mailgun docs show it under `user-variables` in events.
- `user-variables` shape: the doc examples show an empty **list** `[]` when there is none; with variables the Events schema says object (`{"campaign_id": "42"}` in our fixtures, reconstructed). The handler must accept both (`value if isinstance(value, dict) else {}`).
- Matching events to recipients: `message.headers.message-id` in events has no angle brackets (`20260203192638.000be97f99f8cea1@mg.upiixsol.com`); the send call's `id` is described as an RFC-2392 identifier and is returned with brackets in practice (`<…@…>`, **unverified**). Store `provider_message_id` stripped of `<>` and compare stripped. In a batch call, one `id` covers all recipients, so the webhook must match on `(message-id, recipient)`, not on message-id alone. Our own `v:campaign_id` plus the recipient address (normalized) is the stable key; the `recipient` field of every event carries the address.

## 6. Webhook payloads
Source: <https://documentation.mailgun.com/docs/mailgun/user-manual/webhooks/webhook-payloads> (2026-11-17). The page says the payloads are non-exhaustive and fields are additive: **read only the fields below and ignore the rest**.

**Body shape — documented conflict.** The payload page shows each event as a flat object. The signing page says event webhooks "deliver them as a JSON object named `signature`, alongside `event-data`". Mailgun's long-standing format (and the Node snippet's `payload.signature`) is `{"signature": {...}, "event-data": {<event>}}`. The fixtures use that wrapper; UPS-077 should read `body["event-data"]` when present and otherwise fail with 400 (a flat body has no signature to check, so it is rejected anyway). Confirm with one real webhook delivery (**unverified**).

Common fields of `event-data`: `event`, `id`, `timestamp` (float, seconds), `log-level`, `recipient`, `recipient-domain`, `tags`, `user-variables`, `message.headers.message-id`, `domain.name`, `flags.is-test-mode` (absent from `unsubscribed`/`complained`).

| Event | Fixture | Distinguishing fields |
|---|---|---|
| `delivered` | `event_delivered.json` | `log-level: info`, `delivery-status.code: 250`, `delivery-status.message: "OK"`, `tls` |
| `failed`, permanent | `event_failed_permanent.json` | `severity: "permanent"`, `reason: "bounce"`, `log-level: error`, `delivery-status.code: 550`, `enhanced-code: "5.5.0"`, `bounce-type: "hard"` |
| `failed`, temporary | `event_failed_temporary.json` | `severity: "temporary"`, `reason: "generic"`, `log-level: warn`, `delivery-status.code: 421`, `retry-seconds: 600`; Mailgun retries, so this is **not** a final status |
| `complained` | `event_complained.json` | no `flags`, no `delivery-status`; `message.headers` has `to`, `from`, `subject` |
| `unsubscribed` | `event_unsubscribed.json` | `tags: ["*"]`, `ip`, `client-info`, `geolocation`; fired by Mailgun's own unsubscribe link; no `flags`, no `delivery-status` |

Mapping for UPS-077: `delivered` → `delivered`; `failed`+`permanent` → `bounced` and a `mail_suppressions` row (`bounced`); `failed`+`temporary` → no change (log the code only); `complained` → `complained` and suppress; `unsubscribed` → suppress (`unsubscribed`). `opened`/`clicked` are not expected with `o:tracking=no`; ignore unknown events with 200 (an error status makes Mailgun retry).

The older Mailgun naming `permanent_fail`/`temporary_fail` still appears in the webhook-settings table (<https://documentation.mailgun.com/docs/mailgun/user-manual/webhooks/webhooks>): that is the name of the *subscription*, the payload event is `failed` + `severity`. Do not branch on the old names.

PII and logs: the payload carries the recipient address, `message.headers.to` and IPs. Per plan §Logs, log only `event`, ids and counts, never the body.

## 7. Webhook signature
Source: <https://documentation.mailgun.com/docs/mailgun/user-manual/webhooks/securing-webhooks> (2026-11-17).
- Fields: `signature.timestamp` (string of integer seconds), `signature.token` (random, 50 chars), `signature.signature` (hex). Subaccount events add `parent-signature` (not used by us).
- Key: the account-wide **HTTP webhook signing key** (Settings → API Security), **not** the API key or the domain key. It is `MAILGUN_WEBHOOK_SIGNING_KEY`.
- Recipe: `hex(HMAC_SHA256(key = signing key, message = timestamp + token))`, concatenated with no separator, compared with `signature`. Python:

```python
import hashlib, hmac, time

def verify(signing_key: str, timestamp: str, token: str, signature: str, max_age: int = 300) -> bool:
    expected = hmac.new(signing_key.encode(), (timestamp + token).encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return False
    try:
        return abs(time.time() - int(timestamp)) <= max_age
    except ValueError:
        return False
```
- Docs: optionally cache `token` and reject repeats (replay), and optionally check the timestamp is "not too far from the current time", with the warning "don't be too aggressive". No number is given: plan's 5 minutes is our choice; Mailgun retries failed deliveries later, so a late retry would be rejected and the event lost. Mitigate by answering 200 for everything verified and idempotent updates (status only moves forward).
- Fixtures sign with the fake key `test-signing-key-not-a-real-secret`; with that key the five files verify. Note the hash covers only `timestamp + token`, not the body: an attacker who replays a captured `signature` with another body passes unless the token is single-use. The in-memory token cache is therefore required, not optional (ADR 0002 notes it is per process).
- Optional second check, not planned: the TLS client certificate with CN `webhooks.mgsend.net`.

## Open questions for victor (run once, key in `.env`, test mode only)
1. Header substitution in a batch (§3). If it works, UPS-073 batches; if not, the fallback stays.
2. Exact bodies of the 200/400/401 responses to replace the reconstructed `messages_*.json`.
3. Region of the `mg.upiixsol.com` domain (US/EU) → `MAILGUN_API_BASE`.
4. One real webhook delivery to confirm the `event-data` wrapper and the `user-variables` object.

No key was read, printed or committed by this spike.
