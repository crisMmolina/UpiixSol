# Plan 005 · Composer redesign and templates
Spec: `docs/specs/005-plantillas-compositor/spec.md` · builds on plans 003 and 004 · Human owner: victor

## Design
```
Correos ─ 1 Plantilla ──► TemplateGallery (built-in + saved + blank, thumbnails via POST /api/mail/preview)
        ─ 2 Contenido ──► EmailCanvas (React mirror of the email) ⇄ BlockProperties (side panel / bottom sheet)
        │                  BlockInserter ("+"), drag + Alt+↑/↓, duplicate, delete + undo
        │                  "Ver como llega" → EmailPreview (server HTML, sandboxed iframe, as today)
        ─ 3 Destinatarios y envío ──► AudiencePicker, sender, Reply-To, quota, "Revisar y enviar"
State: one composer reducer (subject, preheader, blocks, sender, reply_to, audience) + local draft (localStorage).
```
- **Why a React canvas and not editing inside the server iframe:** the server HTML is the source of truth for what is sent, but it is a sandboxed, script-less document; editing inside it would mean injecting scripts or contenteditable into email HTML. The canvas reuses the renderer's theme tokens (exported from the API with the preview: colors, logo URL, sender block) so it matches the email closely, and "Ver como llega" shows the exact server render. Typing is local; the server is asked only for the debounced exact preview.
- **Inline text:** auto-growing textareas styled like the email text; a toolbar wraps the selection with `**`, `*` or `[texto](url)`; unfocused blocks show the formatted text. No rich-text dependency.
- **Event placeholder:** an event block with `placeholder: true` is valid in templates and preview (rendered as a sample card) and refused with 422 on create/send ("Completa el evento antes de enviar").
- **Render-only preview:** `POST /api/mail/preview` without `audience` renders with the caller's sender for thumbnails and the canvas theme.
- **Built-in templates** in `app/services/mail_templates_builtin.py` (Python data, Spanish placeholders, validated by the same `Blocks` schema at import time), served with the saved ones by one endpoint.

## Data and migrations
Migration `0011_mail_templates` (down_revision `0010`), expand-only: table `mail_templates` (id, scope `site`|`academy`, academy_id → academies CASCADE nullable, name String(60), description String(140), subject, preheader, content JSON (blocks, version), created_by → users SET NULL, created_at, updated_at; unique (scope, academy_id, lower(name))). Round-trip only on a temp SQLite and CI's localhost Postgres (UPS-084 guard).

## Contracts
| Method · path | Who | Notes |
|---|---|---|
| `GET /api/mail/templates` | superadmin, academy_admin | built-ins + UpiixSol + own club (club admin) or all (superadmin); `{id, kind: builtin|saved, scope, name, description, subject, preheader, blocks}` |
| `POST /api/mail/templates` | superadmin (site), academy_admin (own club) | `{name, description?, subject, preheader?, blocks}`; scope from the DB user |
| `PATCH /api/mail/templates/{id}` · `DELETE` | owner scope only | built-ins are read-only (id `builtin:<slug>`, 404/405 on write) |
| `POST /api/mail/preview` | as today | also returns `theme` (colors, logo email URL, sender block text) for the canvas |
Matrix rows for every write endpoint. Web types mirror `MailTemplate` and the preview `theme`.

## Threat model (STRIDE)
| Threat | Vector | Mitigation | Test |
|---|---|---|---|
| Elevation of privilege | Club admin edits UpiixSol or another club's template | scope from `users.academy_id`; ownership checked on PATCH/DELETE | test_academy_admin_cannot_edit_site_or_other_club_template |
| Tampering | Template with script or bad links | same `Blocks` validation and renderer as campaigns | test_template_blocks_validated_like_campaigns |
| Information disclosure | Template leaks addresses or audiences | templates never store audience, sender or Reply-To | test_saved_template_has_no_audience_or_reply_to |
| Information disclosure | Local draft on a shared computer | draft key per user id; cleared on logout, send and discard | e2e test_draft_cleared_on_logout |

## Rollout and rollback
Ships behind the existing `MAIL_ENABLED`. Old campaigns and history unchanged. Rollback = revert the web composer; the templates API is additive.

## Tasks
UPS-100 (contract: templates table, built-ins, preview theme) · UPS-101 (templates API) · UPS-102 (composer shell: 3 steps, reducer, local draft) · UPS-103 (email canvas: inline edit, inserter, drag, properties) · UPS-104 (template gallery + save as template).
