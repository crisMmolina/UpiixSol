# Plan 006 · Combined recipients and delivery detail
Spec: `docs/specs/006-destinatarios-entregas/spec.md` · builds on plans 003, 004, 005 · Human owner: victor

## Design
```
Step 3 "Destinatarios y envío"
  AudienceSources (chips: Todo UpiixSol · Un club · Un rol · Personas · Correos de fuera)
      │ audience = {kind: "mix", sources, user_ids, exclude_user_ids, emails}  (composer reducer)
      ▼
  POST /api/mail/audience/preview  → counts (receives · removed by you · cannot, by reason) + quota
  POST /api/mail/audience/list     → cursor page of people (checkbox state, origin, address in scope)
  RecipientList (search, "Cargar más", uncheck = exclude_user_ids, typed addresses removable)
      │ create/send re-resolve the same `mix` on the server (mail_audience._compute)
History
  History row → DeliveryDetail: counts + GET /api/mail/campaigns/{id}/recipients?status=&q=&cursor=
             → "Usar de nuevo" → composer ?paso=plantilla&reusar=<id> (UPS-104 loads GET /campaigns/{id} content)
```
- **Why a new audience kind and not client-side expansion into user ids:** "Todo UpiixSol" can be thousands of people; sending explicit ids would hit the 50-id cap, freeze the list at compose time and let a crafted body add out-of-scope ids. `mix` keeps sources symbolic, so the server re-resolves them at send time with the same scope checks, and the client only sends the exceptions.
- **Old kinds stay valid** (`all`, `academy`, `role`, `individual`): the API keeps accepting them and history rows keep them. The new composer always sends `mix`.
- **Resolution:** `_compute` gains a `mix` branch: union of each source's users + `user_ids` (deduplicated by user id), minus `exclude_user_ids`, then typed `emails` as today (a typed address equal to a campus user is that user). Exclusions only remove campus users; a typed address is removed by deleting it from `emails`.
- **Scope (unchanged rules):** superadmin any source; club admin only `academy` with their own club, `user_ids` within `_club_members`, and `emails`. `exclude_user_ids` are not scope-checked (removing is always safe) but ids outside the resolved set are ignored.
- **Visibility (victor 2026-11-20):** the picker search, the audience list and the delivery detail return `email` for every person the caller may pick (superadmin: all; club admin: their club's enrollees and co-admins); club admins' search also matches addresses within that scope. Typed addresses stay blind for club admins in preview and list (no suppression check before sending, as UPS-074). Delivery detail shows every row of the caller's own campaigns: the address was already sent to.
- **Delivery reasons:** `mail_delivery.reason_text(status, error_code)` maps Mailgun reasons (`bounce`, `suppress-bounce`, `suppress-unsubscribe`, `suppress-complaint`, `old`, `generic`, `espblock`, `hardfail`) and send errors (`bad_response`, …) to Spanish; unknown codes → "Motivo: <code>".

## Data and migrations
Migration `0012_mail_audience_mix` (down_revision `0011`), expand-only: widens the `mail_campaigns.audience_kind` CHECK to include `mix` (batch mode on SQLite). Downgrade restores the narrower CHECK (round-trip on an empty temp SQLite and CI's localhost Postgres, UPS-084 guard); rollback on a DB that already has `mix` campaigns = revert the web, not downgrade. No new table: delivery detail reads `mail_recipients` (index on `(campaign_id, status)` added in the same migration).

## Contracts
| Method · path | Who | Notes |
|---|---|---|
| `POST /api/mail/audience/preview` | superadmin, academy_admin | accepts `mix`; returns `{count, removed, excluded:{inactive,suppressed,blocked_domain}}` (`removed` new, default 0) |
| `POST /api/mail/audience/list` | superadmin, academy_admin | body `{audience, q?, state?: receives\|removed\|cannot, cursor?, limit≤50}` → `Page[AudienceMember{user_id?, name, nickname?, email, avatar_url?, origins[], state, reason?}]` |
| `GET /api/mail/recipients` | as today | `email` now returned to club admins for their scope; search matches it |
| `GET /api/mail/campaigns/{id}/recipients` | sender scope as `GET /campaigns/{id}` | `?status=&q=&cursor=&limit≤50` → `Page[DeliveryRow{user_id?, name, email, status, reason_code?, reason?, updated_at}]` |
| `GET /api/mail/campaigns/{id}` | as today | adds `content: {preheader, blocks}` (for "Usar de nuevo") and `details_purged: bool` |
Matrix rows for the new endpoints. `web/src/lib/types.ts` mirrors `MixAudience`, `AudienceMember`, `DeliveryRow`.

## Threat model (STRIDE)
| Threat | Vector | Mitigation | Test |
|---|---|---|---|
| Elevation of privilege | Club admin adds `all`, a role, another club or out-of-club `user_ids` inside `mix` | `check_scope` per source and per id; 403 | test_mix_scope_for_academy_admin |
| Information disclosure | Club admin probes whether a typed address unsubscribed | typed addresses blind in preview and list (no suppression check) for non-superadmins | test_mix_list_does_not_confirm_typed_addresses |
| Information disclosure | Club admin reads another club's delivery detail | same campaign scope as `GET /campaigns/{id}`; 404 | test_delivery_detail_scope |
| Information disclosure | Addresses of people outside the caller's scope | list and search filter by `_club_members` before serializing | test_list_returns_only_in_scope_people_with_email |
| Tampering | Crafted body with huge lists | caps: sources ≤ 10, user_ids ≤ 1000, exclude_user_ids ≤ 5000, emails bounded by the monthly quota | test_mix_caps_are_422 |

## Rollout and rollback
Behind `MAIL_ENABLED`. Backend first (old kinds keep working, so the current composer is unaffected), then the step-3 list and the history detail. Rollback = revert the web; the API changes are additive.

## Tasks
UPS-105 (contract + API: `mix` audience, migration 0012, audience list, visibility) · UPS-106 (delivery detail API + campaign content) · UPS-107 (web: sources + checkbox list in step 3) · UPS-108 (web: delivery detail in the history + "Usar de nuevo") · UPS-104 amended (save on send checked by default + "Enviados recientes").
