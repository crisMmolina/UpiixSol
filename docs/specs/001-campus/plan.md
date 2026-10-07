# Plan 001 · UpiixSol Campus v1

## Design
- Monolith: **FastAPI** (`app/`) + **React/Vite/TS/Tailwind v4** (`web/`); in production FastAPI serves `web/dist` behind nginx. ADR 0001.
- Lightweight multi-tenant: every content table carries `academy_id`; the academy scope is checked in reusable dependencies (`app/security.py`: `current_user`, `require_role`, `require_academy_scope(academy_id)`). No endpoint checks roles by hand.
- Cross-cutting pieces live in the contract task (UPS-002) so features stay disjoint: SQLAlchemy models, initial migration, Pydantic schemas, security, cursor pagination, media (uploads), sanitization, seed.
- Front end: each feature lives in `web/src/features/<f>/index.tsx` and exports `routes` (react-router). `App.tsx` collects them with `import.meta.glob`, so no one edits it after setup. Theme: `ThemeProvider` injects `--academy-primary|secondary|accent|accent-2` from the API on top of a light base theme (cream `#FBF8EF`, text `#1F2A24`).
- Alternatives discarded: Django (heavier, slower for the team), Supabase/Firebase (vendor lock-in plus RLS to learn under a deadline), Moodle (no per-academy identity).

## Data and migrations
- All entities from `IDEA.md` §6 go in `app/models/`, with Alembic migration `0001_initial` (reversible `downgrade`). Indexes: every FK, `users.email` (unique), `users.boleta` (unique, nullable), `academies.slug` (unique), `posts(channel_id, created_at)`, `lesson_progress(user_id)`; unique `lesson_progress(user_id, lesson_id)` and `enrollments(user_id, academy_id)`.
- Hidden posts: `hidden_by_id`, `hidden_at` columns (audit trail).
- Soft delete: `is_active` on `users` and `academies`.
- Later changes: one migration per PR, expand → migrate → contract.
- Dev uses SQLite; tests and production use PostgreSQL 16 (compose). Tests use SQLite in memory by default, plus a CI job against Postgres.

## Contracts
- REST under `/api`, versioned by the Pydantic schemas in `app/schemas/` (owner UPS-002). TS mirror in `web/src/lib/types.ts`.
- Uniform error format: `{"error": {"code": "...", "message": "...", "details": ...}}`.
- Pagination: `?cursor=<opaque>&limit<=50` → `{"items": [...], "next_cursor": str | null}`.
- Endpoints per task: see `.uak/TASKS.md` (each task lists its own).

## Threat model (STRIDE)
| Threat | Vector | Mitigation | Test |
|---|---|---|---|
| Spoofing | brute force on login, stolen JWT | argon2id, rate limit 5/min/IP, 15-min access JWT, refresh in an `HttpOnly; Secure; SameSite=Lax` cookie with rotation | `test_auth.py::test_rate_limit`, `test_refresh_rotation` |
| Tampering | admin edits another academy, IDs in the URL | `require_academy_scope` per resource (resolves the content's `academy_id` from the DB, never from the body) | `test_permissions_matrix.py` |
| Repudiation | moderator hides a post and denies it | `hidden_by_id` + `hidden_at`, structured logs with `user_id` | `test_community.py::test_hide_audit` |
| Information disclosure | boleta/email leaked in the community or in errors | public schemas `PublicUser{id,nickname,avatar_url}`; no PII in logs; generic errors | `test_community.py::test_no_pii` |
| Denial of service | huge lists, large images, post spam | max 50 per page, upload limits, 10 posts/min/user, Pillow `MAX_IMAGE_PIXELS` | `test_media.py`, pagination tests |
| Elevation of privilege | member self-registers as admin, mass assignment | `RegisterIn` without `role`; `extra="forbid"` on input schemas; only superadmins create admins | `test_auth.py::test_register_ignores_role` |
| XSS | markdown/HTML in posts, descriptions, SVG | sanitize with `nh3` on save, React does not use `dangerouslySetInnerHTML` without sanitizing, SVG served with `Content-Security-Policy: script-src 'none'` | `test_sanitize.py` |
| Open redirect / SSRF | `youtube_url`, `link_url` | strict YouTube id parsing; links limited to `http(s)`; the server never fetches user URLs | `test_youtube.py` |

## Observability
JSON logs (`request_id`, `user_id`, route, status, latency) with no email or boleta; `GET /api/health` (process) and `GET /api/ready` (DB).

## Rollout and rollback
v1 has no feature flags: the delivery is the first release. Rollback = redeploy the previous image plus `alembic downgrade -1` (reversible migrations). Daily backup with `pg_dump` (runbook in UPS-015).

## Cost
One VPS (~USD 5–10/month) with compose; YouTube embed with no key. No paid APIs.

## Tasks
UPS-001 … UPS-019 in `.uak/TASKS.md`. Each starts with a failing test.
