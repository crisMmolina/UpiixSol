# Mailgun fixtures (UPS-071)

Event files are the JSON examples of
<https://documentation.mailgun.com/docs/mailgun/user-manual/webhooks/webhook-payloads>
(checked 2026-11-17), wrapped as `{"signature": {...}, "event-data": {...}}` per
<https://documentation.mailgun.com/docs/mailgun/user-manual/webhooks/securing-webhooks>.

Changes made: recipients are `@example.com`; sender and domain are `avisos@mg.upiixsol.com` / `mg.upiixsol.com`;
IP addresses are documentation ranges (RFC 5737); `user-variables` is `{"campaign_id": "42"}` in
`delivered` and both `failed` files (the docs show only `[]`). They are NOT captured from a live
run: no Mailgun call was made (see `docs/spikes/mailgun.md`).

`signature` is a real HMAC-SHA256 over `timestamp + token` with the fake key
`test-signing-key-not-a-real-secret` (not a secret), so tests can verify it. Timestamp `1770920772` is fixed:
tests that check the age must patch the clock.

`messages_*.json` are `{status, content_type, body}`. The Messages API reference gives the field names (`id`, `message`)
but no example body, so these three are reconstructed and unverified; replace them with recordings once a
real test-mode call is made.
