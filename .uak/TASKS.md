# TASKS · stateless backlog

State lives on the `claims` branch (`uak status`); this file holds only tasks. IDs are `UPS-NNN`.
Priority is `P0/P1/P2`. Type is `setup/contract/spike/feature/bug/integration/demo/docs`. Check the graph with `uak graph`.
Spec: `docs/specs/001-campus/spec.md` · Plan: `docs/specs/001-campus/plan.md` · Product: `IDEA.md`. UI in Spanish (Mexico).
Every commit and PR goes out under the human's identity, **without** `Co-Authored-By` or "Generated with" (PROJECT principle 5).

## UPS-001 · Repo skeleton: FastAPI + Vite running, CI and dependencies

- **Type:** setup
- **Priority:** P0
- **Estimate:** 90 min
- **Rubric / Spec:** S001 robustness · `docs/specs/001-campus/plan.md` §Design
- **Depends on:** None
- **Uses contract:** None
- **Related:** UPS-002
- **Paths:** pyproject.toml, uv.lock, .python-version, .gitignore, app/__init__.py, app/main.py, app/config.py, app/db.py, app/errors.py, app/ratelimit.py, app/routers/__init__.py, app/services/__init__.py, app/tests/__init__.py, app/tests/test_health.py, alembic.ini, app/migrations/env.py, app/migrations/script.py.mako, web/package.json, web/package-lock.json, web/vite.config.ts, web/tsconfig.json, web/tsconfig.app.json, web/tsconfig.node.json, web/eslint.config.js, web/index.html, web/src/main.tsx, web/src/App.tsx, web/src/vite-env.d.ts, .github/workflows/, .env.example, README.md, CHANGELOG.md, .uak/bin/smoke-project
- **Freeze-Allowed:** no
- **Acceptance:**
  - Python deps installed in one go: fastapi, uvicorn[standard], sqlalchemy>=2, alembic, psycopg[binary], pydantic-settings, pydantic[email], argon2-cffi, pyjwt, slowapi, python-multipart, pillow, nh3, httpx; dev: pytest, pytest-cov, ruff, playwright.
  - Web deps installed in one go: react 19, react-router, tailwindcss + @tailwindcss/vite, motion, @phosphor-icons/react, @fontsource/fredoka, @fontsource-variable/inter, dompurify, marked.
  - `app/main.py` auto-discovers `app/routers/*`, registers uniform JSON errors (`app/errors.py`), the slowapi limiter (`app/ratelimit.py`), CORS from `CORS_ORIGINS`, `/media` static files, and serves `web/dist`. `GET /api/health` → `{"status":"ok"}`; `GET /api/ready` checks the DB.
  - `app/config.py` reads everything from env (`DATABASE_URL`, `JWT_SECRET`, `CORS_ORIGINS`, `MEDIA_DIR`, `SEED_DEFAULT_PASSWORD`); `.env.example` with no real values.
  - Alembic configured against `app.db.Base.metadata` (empty `versions/` for UPS-002).
  - `web/src/App.tsx` builds the router from `import.meta.glob("./features/*/index.tsx")`, where each feature exports `routes: RouteObject[]`; no one edits it after this task.
  - CI (`.github/workflows/`): ruff + pytest with `--cov=app` (coverage target 100 %, initial floor `--cov-fail-under=90`) + `npm ci && lint && build`; a job against Postgres 16 as a service.
  - `bash .uak/bin/smoke` exits 0
- **Verify:** `uv run ruff check app && uv run pytest -q app/tests/test_health.py && npm --prefix web run build`
- **Next step:** follow `.uak/stacks/fastapi-react/STACK.md` §Backend setup, adding the full dependency list above in a single `uv add`.

## UPS-002 · Contract: models, migration 0001, schemas, security, seed and DESIGN.md

- **Type:** contract
- **Priority:** P0
- **Estimate:** 180 min
- **Rubric / Spec:** S001 data, roles · `docs/specs/001-campus/plan.md` §Data, §Contracts, §STRIDE
- **Depends on:** UPS-001
- **Uses contract:** None
- **Related:** UPS-004, UPS-005, UPS-006, UPS-007, UPS-008, UPS-009
- **Paths:** app/models/, app/schemas/, app/migrations/versions/, app/security.py, app/pagination.py, app/sanitize.py, app/services/media.py, app/services/progress.py, app/fixtures/, app/seed.py, app/tests/conftest.py, app/tests/test_security.py, app/tests/test_pagination.py, app/tests/test_sanitize.py, app/tests/test_media.py, app/tests/test_progress.py, app/tests/test_seed.py, web/DESIGN.md, web/src/lib/types.ts, web/public/brand/
- **Freeze-Allowed:** no
- **Acceptance:**
  - SQLAlchemy models for every entity in `IDEA.md` §6 (+ `posts.hidden_by_id/hidden_at`, `refresh_tokens`) and a reversible migration `0001_initial` with the indexes from plan §Data; `alembic upgrade head && alembic downgrade base` runs green against SQLite.
  - `app/schemas/`: input schemas with `extra="forbid"`, `PublicUser{id,nickname,avatar_url}` (never boleta/email), `Page[T]{items,next_cursor}`, uniform error.
  - `app/security.py`: argon2id hash/verify, access/refresh JWT, dependencies `current_user`, `require_role(*roles)`, `require_academy_scope(academy_id)` (superadmin passes; academy_admin only with `user.academy_id == academy_id`; otherwise 403).
  - `app/pagination.py` (opaque cursor, limit ≤ 50), `app/sanitize.py` (nh3), `app/services/media.py` (real type png/jpg/webp/svg, 2/5 MB, resize), `app/services/progress.py` (completed ÷ published, next unfinished lesson).
  - `python -m app.seed` is idempotent: the 6 accounts in §2.3 with `must_change_password`, the full UpiixIA demo case (§3, `demo_data`), Feed/General/#upiixia channels, alumno.demo at 50 %, password from `SEED_DEFAULT_PASSWORD`.
  - `conftest.py`: SQLite DB per test, `client`, and `as_superadmin/as_admin_ia/as_member` fixtures.
  - `web/DESIGN.md`: light theme, cream `#FBF8EF`, text `#1F2A24`, palettes from IDEA §0.1, Fredoka + Inter, `--academy-*` tokens, AA contrast checked. `web/public/brand/` = copies of `assets/brand/`. `web/src/lib/types.ts` mirrors the schemas.
- **Verify:** `uv run pytest -q app/tests/test_security.py app/tests/test_pagination.py app/tests/test_sanitize.py app/tests/test_media.py app/tests/test_progress.py app/tests/test_seed.py`
- **Next step:** write `app/tests/test_progress.py` (2 of 4 → 50 %, next = lesson 3) and then `app/models/`.

## UPS-003 · Spike: parse YouTube URLs and the embed fallback

- **Type:** spike
- **Priority:** P0
- **Estimate:** 30 min
- **Rubric / Spec:** S001 YouTube criterion · `IDEA.md` §7
- **Depends on:** None
- **Uses contract:** None
- **Related:** UPS-007, UPS-008
- **Paths:** app/services/youtube.py, app/tests/test_youtube.py, docs/spikes/youtube.md
- **Freeze-Allowed:** no
- **Acceptance:**
  - `extract_video_id(url)` accepts watch, youtu.be, shorts, embed, m.youtube and `youtube-nocookie`; rejects other domains, `javascript:` and malformed ids (11 chars `[A-Za-z0-9_-]`).
  - `embed_url(id)` → `https://www.youtube-nocookie.com/embed/{id}`, `thumbnail_url(id)` → `https://img.youtube.com/vi/{id}/hqdefault.jpg`.
  - Pure Python (stdlib only); `docs/spikes/youtube.md` records the URL formats, the "Video no disponible" fallback and the official docs link.
- **Verify:** `python3 -m unittest app.tests.test_youtube`
- **Next step:** write `app/tests/test_youtube.py` with 8 real URLs and 5 invalid ones.

## UPS-004 · Web shell: layout, base theme, academy theme and API client

- **Type:** feature
- **Priority:** P0
- **Estimate:** 120 min
- **Rubric / Spec:** S001 visual identity · `IDEA.md` §0.1, `web/DESIGN.md`
- **Depends on:** UPS-001
- **Uses contract:** UPS-002, UPS-005
- **Related:** UPS-006
- **Paths:** web/src/index.css, web/src/lib/api.ts, web/src/lib/auth.tsx, web/src/lib/theme.tsx, web/src/lib/providers.tsx, web/src/components/, web/src/layouts/
- **Freeze-Allowed:** no
- **Acceptance:**
  - `api.ts`: fetch with the access token in memory, automatic refresh on 401 (refresh cookie) and a single retry; errors parsed from the uniform format.
  - `auth.tsx`: `AuthProvider`, `useAuth()`, `RequireRole` (redirects to /login or to the role's home).
  - `providers.tsx`: default export wrapping the app in `AuthProvider` (contract of `web/src/App.tsx`, UPS-001).
  - `theme.tsx`: `AcademyTheme` applies `--academy-primary|secondary|accent|accent-2` and the logo; UpiixSol palette at the campus root.
  - `layouts/`: `CampusLayout` (header with the UpiixSol wordmark, nav: Inicio, Academias, Comunidad, Calendario, Galería, Blog, avatar menu) and `AcademyLayout` (academy logo and nav); both responsive with a mobile menu.
  - `components/`: Button, Card, ProgressBar, Badge, EmptyState (with mascot), Skeleton, Modal/Drawer, Field; light theme only; visible focus.
- **Verify:** `npm --prefix web run lint && npm --prefix web run build`
- **Next step:** tokens in `web/src/index.css` from `web/DESIGN.md`, then `lib/api.ts`.

## UPS-005 · Single login, member registration and session (flow step 1)

- **Type:** feature
- **Priority:** P0
- **Estimate:** 150 min
- **Rubric / Spec:** S001 auth criteria · flow step 1
- **Depends on:** UPS-001, UPS-002
- **Uses contract:** UPS-004
- **Related:** UPS-014
- **Paths:** app/routers/auth.py, app/services/auth.py, app/tests/test_auth.py, web/src/features/auth/
- **Freeze-Allowed:** no
- **Acceptance:**
  - `POST /api/auth/register` (name, 10-digit boleta, email, password ≥ 8, privacy notice accepted) → member + session; duplicate boleta/email → generic 409; a `role` in the body is rejected (422).
  - `POST /api/auth/login`, `POST /api/auth/refresh` (rotation; reusing a refresh token revokes the chain), `POST /api/auth/logout`, `GET /api/auth/me` (includes `must_change_password`, `role`, `academy_slug`).
  - Rate limit 5/min/IP on login and register → 429. Inactive user → 401.
  - UI `/login`: "Entrar" / "Crear cuenta" tabs, UpiixSol mascot and wordmark, validation errors in Spanish, redirect by role.
- **Verify:** `uv run pytest -q app/tests/test_auth.py && npm --prefix web run build`
- **Next step:** `app/tests/test_auth.py::test_register_duplicate_boleta_409`.

## UPS-006 · Campus home and academy home with re-theming (flow step 2)

- **Type:** feature
- **Priority:** P0
- **Estimate:** 180 min
- **Rubric / Spec:** S001 re-theming and "Continuar" criteria · flow step 2
- **Depends on:** UPS-001, UPS-002
- **Uses contract:** UPS-004, UPS-007
- **Related:** UPS-011, UPS-013
- **Paths:** app/routers/academies.py, app/services/academies.py, app/tests/test_academies.py, web/src/features/home/, web/src/features/academy/
- **Freeze-Allowed:** no
- **Acceptance:**
  - `GET /api/home`: hero (HomeContent), active academies, featured projects, upcoming events, recent activity (≤ 5 posts with `PublicUser`).
  - `GET /api/academies` (paginated), `GET /api/academies/{slug}` (branding), `GET /api/academies/{slug}/home`: welcome, `continue {lesson_id, title, percent}` computed with `services/progress.py`, my routes with %, recent resources, latest posts from its channel, upcoming events. `POST /api/academies/{slug}/enroll` (idempotent).
  - Inactive academy → 404. No N+1 (queries counted in a test ≤ fixed number).
  - UI: campus home with mascot and academy cards; on entering `/a/{slug}` the theme and logo switch instantly; with alumno.demo, "Continuar: Clase 3 · 50 %" is visible.
- **Verify:** `uv run pytest -q app/tests/test_academies.py && npm --prefix web run build`
- **Next step:** `test_academy_home_continue_shows_lesson3_50pct` using the seed.

## UPS-007 · Learning routes, course player and persistent progress (flow step 3)

- **Type:** feature
- **Priority:** P0
- **Estimate:** 210 min
- **Rubric / Spec:** S001 progress criterion · flow step 3 · `docs/ref/player-reference.png` (layout only)
- **Depends on:** UPS-001, UPS-002
- **Uses contract:** UPS-003, UPS-004
- **Related:** UPS-006, UPS-008
- **Paths:** app/routers/learning.py, app/services/learning.py, app/tests/test_learning.py, web/src/features/learning/
- **Freeze-Allowed:** no
- **Acceptance:**
  - `GET /api/academies/{slug}/routes`, `GET /api/routes/{id}` (modules with published lessons, `completed/total`, %), `GET /api/lessons/{id}` (embed, sanitized description, links, prev/next, updates `last_viewed_at`), `POST /api/lessons/{id}/complete` and `DELETE` (undo); unpublished lesson → 404 for members.
  - Completing lesson 3 as alumno.demo → 75 %; after reloading, it is still 75 %.
  - UI: left sidebar (title, % bar, lesson search, collapsible modules with check and `x/y`, current lesson highlighted, duration), 16:9 video (`youtube-nocookie`), Anterior/Siguiente/Marcar como completada, Descripción and Recursos de la clase; "Video no disponible" fallback; drawer on mobile.
- **Verify:** `uv run pytest -q app/tests/test_learning.py && npm --prefix web run build`
- **Next step:** `test_complete_lesson_moves_progress_50_to_75`.

## UPS-008 · Academy panel: identity, routes → modules → lessons, enrollees (flow step 5)

- **Type:** feature
- **Priority:** P0
- **Estimate:** 210 min
- **Rubric / Spec:** S001 academy-scope criterion · flow step 5
- **Depends on:** UPS-001, UPS-002
- **Uses contract:** UPS-003, UPS-004
- **Related:** UPS-007, UPS-009
- **Paths:** app/routers/academy_admin.py, app/services/academy_admin.py, app/tests/test_academy_admin.py, web/src/features/academy-admin/
- **Freeze-Allowed:** no
- **Acceptance:**
  - CRUD for routes, modules, lessons (YouTube URL validated with UPS-003, sanitized markdown, links), publish/unpublish, reorder with up/down; `PATCH /api/academies/{id}/branding` (colors as `#RRGGBB`, welcome text) and logo/mascot upload (`services/media.py`).
  - Enrollees: list (paginated, shows boleta only to admin/superadmin), enroll/unenroll members.
  - All writes use `require_academy_scope`; admin.ia editing another academy → 403 (dedicated test).
  - UI at `/panel/academia`: tabs Identidad (live preview of colors), Contenido (tree with up/down arrows), Inscritos.
- **Verify:** `uv run pytest -q app/tests/test_academy_admin.py && npm --prefix web run build`
- **Next step:** `test_admin_ia_cannot_patch_other_academy_403`.

## UPS-009 · Superadmin panel: academies, users and home page (flow step 6)

- **Type:** feature
- **Priority:** P0
- **Estimate:** 210 min
- **Rubric / Spec:** S001 multi-academy criterion · flow step 6
- **Depends on:** UPS-001, UPS-002
- **Uses contract:** UPS-004
- **Related:** UPS-008, UPS-013
- **Paths:** app/routers/admin.py, app/services/admin.py, app/tests/test_admin.py, web/src/features/superadmin/
- **Freeze-Allowed:** no
- **Acceptance:**
  - `POST/PATCH /api/admin/academies` (slug, name, colors, logo; soft delete with `is_active`); creating one also creates its channel in the same transaction.
  - `GET/POST/PATCH /api/admin/users` (paginated, filters by role/academy): create academy_admin (with `academy_id`) and members, activate/deactivate, reset password (`must_change_password=true`).
  - `PUT /api/admin/home` (HomeContent). Superadmin only; any other role → 403.
  - UI at `/admin`: Academias (list + form with color picker and logo), Usuarios (table + create admin), Página principal.
- **Verify:** `uv run pytest -q app/tests/test_admin.py && npm --prefix web run build`
- **Next step:** `test_create_academy_creates_channel`.

## UPS-010 · Permission matrix: role × write endpoint (P0)

- **Type:** integration
- **Priority:** P0
- **Estimate:** 90 min
- **Rubric / Spec:** S001 permissions criteria · `IDEA.md` §2.1, §8
- **Depends on:** UPS-005, UPS-006, UPS-007, UPS-008, UPS-009
- **Uses contract:** UPS-002
- **Related:** UPS-011, UPS-012, UPS-013
- **Paths:** app/tests/test_permissions_matrix.py, docs/permissions-matrix.md
- **Freeze-Allowed:** no
- **Acceptance:**
  - Test parametrized from `app.routes`: every non-GET `/api/*` endpoint is exercised as anonymous (401), member, admin of the same academy, admin of another academy, and superadmin, with the expected status from §2.1.
  - The test fails if a new write endpoint does not appear in the table (no silent gaps).
  - `docs/permissions-matrix.md` generated with the % of the matrix covered.
- **Verify:** `uv run pytest -q app/tests/test_permissions_matrix.py`
- **Next step:** list `app.routes` filtered by method ≠ GET and build the expectations table.

## UPS-011 · Community: Feed, General and per-academy channels, posts, comments, moderation (flow step 4)

- **Type:** feature
- **Priority:** P1
- **Estimate:** 240 min
- **Rubric / Spec:** S001 community criteria · flow step 4
- **Depends on:** UPS-001, UPS-002
- **Uses contract:** UPS-004
- **Related:** UPS-006, UPS-018
- **Paths:** app/routers/community.py, app/services/community.py, app/tests/test_community.py, web/src/features/community/
- **Freeze-Allowed:** no
- **Acceptance:**
  - `GET /api/channels`, `GET /api/channels/{id}/posts` (cursor; Feed aggregates General + academies), `POST /api/channels/{id}/posts` (sanitized body, optional image via media, `http(s)` link), comments (paginated), `POST /api/posts/{id}/hide` (superadmin: everything; academy_admin: their own channel; records `hidden_by_id/hidden_at`).
  - Rate limit 10 posts/min/user → 429. The response only exposes `PublicUser` (test with no boleta/email in the JSON).
  - UI at `/comunidad`: Discord-style layout (channel column, feed, composer with image), refresh every 30 s, `#upiixia` shortcut from the academy.
- **Verify:** `uv run pytest -q app/tests/test_community.py && npm --prefix web run build`
- **Next step:** `test_post_in_academy_channel_appears_in_feed`.

## UPS-012 · Academy resources (cards filterable by type)

- **Type:** feature
- **Priority:** P1
- **Estimate:** 120 min
- **Rubric / Spec:** S001 · `IDEA.md` §9 Recursos
- **Depends on:** UPS-001, UPS-002
- **Uses contract:** UPS-004
- **Related:** UPS-006, UPS-008
- **Paths:** app/routers/resources.py, app/services/resources.py, app/tests/test_resources.py, web/src/features/resources/
- **Freeze-Allowed:** no
- **Acceptance:**
  - `GET /api/academies/{slug}/resources?type=` (paginated); admin CRUD for the academy (`require_academy_scope`), url `http(s)` or uploaded file.
  - UI: cards with document/link/video/other filter, plus a management form inside the academy panel.
- **Verify:** `uv run pytest -q app/tests/test_resources.py && npm --prefix web run build`
- **Next step:** `test_admin_other_academy_cannot_create_resource_403`.

## UPS-013 · Events and calendar (month view + list, academy filter)

- **Type:** feature
- **Priority:** P1
- **Estimate:** 150 min
- **Rubric / Spec:** S001 · flow step 6 (global event)
- **Depends on:** UPS-001, UPS-002
- **Uses contract:** UPS-004
- **Related:** UPS-006, UPS-009
- **Paths:** app/routers/events.py, app/services/events.py, app/tests/test_events.py, web/src/features/events/
- **Freeze-Allowed:** no
- **Acceptance:**
  - `GET /api/events?from&to&academy=` (paginated), `POST/PATCH/DELETE /api/events`: superadmin global or any academy; academy_admin only their own (`academy_id` required); `ends_at >= starts_at`.
  - UI: `/calendario` (month + list, filter) and the academy's Eventos tab.
- **Verify:** `uv run pytest -q app/tests/test_events.py && npm --prefix web run build`
- **Next step:** `test_admin_ia_cannot_create_global_event_403`.

## UPS-014 · My account: profile, avatar, change email and password

- **Type:** feature
- **Priority:** P1
- **Estimate:** 120 min
- **Rubric / Spec:** S001 · `IDEA.md` §2.3
- **Depends on:** UPS-001, UPS-002
- **Uses contract:** UPS-004, UPS-005
- **Related:** UPS-005
- **Paths:** app/routers/account.py, app/services/account.py, app/tests/test_account.py, web/src/features/account/
- **Freeze-Allowed:** no
- **Acceptance:**
  - `PATCH /api/account/profile` (nickname, full_name), `POST /api/account/avatar` (media, resized), `POST /api/account/email` and `POST /api/account/password` (require the current password; password change revokes refresh tokens and clears `must_change_password`).
  - UI at `/cuenta`: Perfil and Seguridad tabs; a banner when `must_change_password` (UPS-020 makes the change required).
- **Verify:** `uv run pytest -q app/tests/test_account.py && npm --prefix web run build`
- **Next step:** `test_change_password_requires_current`.

## UPS-015 · Deployment: Docker Compose, nginx, backups and runbook

- **Type:** setup
- **Priority:** P1
- **Estimate:** 90 min
- **Rubric / Spec:** S001 robustness (`docker compose up` from scratch)
- **Depends on:** UPS-001, UPS-002
- **Uses contract:** None
- **Related:** UPS-016
- **Paths:** Dockerfile, .dockerignore, docker-compose.yml, deploy/, docs/runbook.md
- **Freeze-Allowed:** no
- **Acceptance:**
  - `docker compose up --build` brings up db (postgres 16 with a volume), api (migrations + optional seed on start) and nginx (static files, `/media` with cache, security headers, proxy to `/api`).
  - nginx `client_max_body_size 6m`; uvicorn `--proxy-headers --forwarded-allow-ips=<nginx IP>` so the rate limits see the real client IP (security review UPS-005).
  - `deploy/backup.sh` with daily `pg_dump` and rotation; `docs/runbook.md` with deploy, restore, rollback (`alembic downgrade -1`) and rotating the seed passwords.
- **Verify:** `docker compose config -q && bash -n deploy/backup.sh`
- **Next step:** multi-stage `Dockerfile` (node build → python runtime).

## UPS-016 · End-to-end acceptance flow (6 steps) with Playwright

- **Type:** integration
- **Priority:** P1
- **Estimate:** 120 min
- **Rubric / Spec:** S001 · `IDEA.md` §4 and §8 (desktop + mobile)
- **Depends on:** UPS-005, UPS-006, UPS-007, UPS-008, UPS-009, UPS-011, UPS-013
- **Uses contract:** UPS-002
- **Related:** UPS-010, UPS-015
- **Paths:** e2e/, docs/acceptance.md
- **Freeze-Allowed:** no
- **Acceptance:**
  - Python Playwright script covering steps 1–6 on a freshly seeded DB, with reduced motion, at viewports 1280 and 390; screenshots in `e2e/artifacts/` (git-ignored).
  - `docs/acceptance.md` with the result of each step and the commands used.
- **Verify:** `uv run pytest -q e2e`
- **Next step:** fixture that starts uvicorn on `$UAK_PORT` with a temporary DB and the seed.

## UPS-017 · Project gallery and blog

- **Type:** feature
- **Priority:** P2
- **Estimate:** 180 min
- **Rubric / Spec:** S001 · `IDEA.md` §9 Galería, Blog
- **Depends on:** UPS-001, UPS-002
- **Uses contract:** UPS-004
- **Related:** UPS-006
- **Paths:** app/routers/gallery.py, app/routers/blog.py, app/services/gallery.py, app/services/blog.py, app/tests/test_gallery.py, app/tests/test_blog.py, web/src/features/gallery/, web/src/features/blog/
- **Freeze-Allowed:** no
- **Acceptance:**
  - Public listing (paginated) and detail by slug; superadmin CRUD with draft/published status; sanitized markdown.
  - UI: blog-style listing + detail; superadmin forms.
- **Verify:** `uv run pytest -q app/tests/test_gallery.py app/tests/test_blog.py && npm --prefix web run build`
- **Next step:** `test_draft_project_not_listed`.

## UPS-018 · Post reactions

- **Type:** feature
- **Priority:** P2
- **Estimate:** 60 min
- **Rubric / Spec:** S001 · `IDEA.md` §8.1 P2
- **Depends on:** UPS-011
- **Uses contract:** UPS-002
- **Related:** UPS-011
- **Paths:** app/routers/reactions.py, app/services/reactions.py, app/tests/test_reactions.py, web/src/features/community/
- **Freeze-Allowed:** no
- **Acceptance:**
  - `PUT/DELETE /api/posts/{id}/reactions/{kind}` idempotent, one per user and kind; counts in the post listing.
- **Verify:** `uv run pytest -q app/tests/test_reactions.py && npm --prefix web run build`
- **Next step:** `test_reaction_idempotent`.

## UPS-019 · Drag-and-drop reordering in the academy panel

- **Type:** feature
- **Priority:** P2
- **Estimate:** 90 min
- **Rubric / Spec:** S001 · `IDEA.md` §8.1 P2
- **Depends on:** UPS-008
- **Uses contract:** UPS-002
- **Related:** UPS-008
- **Paths:** web/src/features/academy-admin/
- **Freeze-Allowed:** no
- **Acceptance:**
  - Drag-and-drop for modules and lessons using the existing reorder endpoint; the arrows remain as the keyboard-accessible fallback.
- **Verify:** `npm --prefix web run lint && npm --prefix web run build`
- **Next step:** evaluate drag-and-drop with no new dependency (native HTML5 DnD) before asking for one.

## UPS-020 · Auth hardening and required password change (security review UPS-005)

- **Type:** bug
- **Priority:** P0
- **Estimate:** 120 min
- **Rubric / Spec:** S001 auth criteria · `docs/specs/001-campus/plan.md` STRIDE
- **Depends on:** UPS-005, UPS-014
- **Uses contract:** UPS-002, UPS-004
- **Related:** UPS-005, UPS-014, UPS-015
- **Paths:** app/routers/auth.py, app/services/auth.py, app/tests/test_auth.py, app/config.py, .env.example, app/security.py, app/models/user.py, app/migrations/versions/0002_password_changed_at.py, app/ratelimit.py, app/tests/test_security.py, web/src/features/auth/, web/src/lib/auth.tsx, web/src/lib/api.ts, app/tests/conftest.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - Refresh rotation claims the token atomically (`UPDATE … WHERE used_at IS NULL`); two concurrent refreshes with the same token → exactly one 200, the other is treated as reuse. A short grace window (≈10 s) answers 401 without revoking the family, so two tabs refreshing at once do not log the user out.
  - Concurrent register with the same email/boleta → 409 (IntegrityError caught in a savepoint), never 500.
  - A password change or reset also invalidates access tokens already issued (`iat` before `password_changed_at`, or a `token_version` claim) (security review UPS-014).
  - Login also rate-limited per normalized email (5/min) besides per IP; `X-Requested-With: fetch` required on login and register.
  - `must_change_password` is enforced: every authenticated endpoint except `GET /api/auth/me`, `POST /api/auth/logout|refresh` and `POST /api/account/password` → 403 `password_change_required`; the UI sends the user to `/cuenta?tab=seguridad` until they change it. Setting `REQUIRE_PASSWORD_CHANGE` (default `true`) can be set to `false` for a demo with the seeded accounts (IDEA §2.3).
- **Verify:** `uv run pytest -q app/tests/test_auth.py app/tests/test_security.py && npm --prefix web run build`
- **Next step:** `test_concurrent_refresh_only_one_wins`.

## UPS-021 · Redesign v2: design system and app shell (white theme, side rail, notifications, transparent logos)

- **Type:** feature
- **Priority:** P0
- **Estimate:** 180 min
- **Rubric / Spec:** S001 · redesign feedback 2026-10-08 (items 1, 2, 5, 6, 7, 10, 11, 15, 21, 24, *skeletons)
- **Depends on:** none
- **Uses contract:** UPS-004
- **Related:** UPS-022, UPS-023, UPS-024, UPS-025, UPS-026, UPS-027, UPS-028
- **Paths:** web/DESIGN.md, web/src/index.css, web/src/components/, web/src/layouts/, web/src/lib/theme.tsx, web/src/lib/notifications.tsx, web/src/lib/providers.tsx, web/public/brand/, web/index.html
- **Freeze-Allowed:** no
- **Contract (published first, so wave 2 starts in parallel):** token and class names stay (`bg-bg`, `bg-surface`, `text-ink`, `text-muted`, `border-line`, `text-link`, `--academy-*`); `Skeleton`, `Card`, `Button`, `Field`, `States`, `Overlay` keep their props (new optional props only). New: `[data-theme="dark"]` scope with the same token names (course view), `useNotifications()` (`notify({id,title,body,action})`), nav routes `/clubes` and `/a/:slug/comunidad`.
- **Acceptance:**
  - Light theme on pure white `#FFFFFF` background with one neutral gray family; AA re-checked and recorded in `web/DESIGN.md` (incl. link color on dark).
  - Layout like the reference campus: left icon rail (labels under icons) with Inicio, Clubes, Comunidad, Calendario, Galería, Blog; slim top bar with logo, notification bell and user menu; mobile = bottom/drawer nav. No footer anywhere.
  - Club context: the rail switches to the club (Inicio, Rutas, Recursos, Comunidad, Eventos), a club switcher, and an obvious "Campus" way back; Comunidad inside a club stays in the club (`/a/:slug/comunidad`).
  - Notifications: on sign-in, transient cards slide in top-right and auto-dismiss; the bell (with unread count) reopens a right-side panel with them. The provisional-password notice moves there (no more banner).
  - Logos and mascots as transparent PNGs (background removed, edges clean), checked on white and on dark.
  - Every shared component has a skeleton variant; subtle motion (hover lift, fade/slide-in, staggered lists, 150–250 ms) with `prefers-reduced-motion` respected.
  - All user-visible "Academia/Academias" in shell and components → "Club/Clubes".
- **Verify:** `npm --prefix web run lint && npm --prefix web run build && uv run pytest -q e2e`
- **Next step:** transparent logos + tokens on white.

## UPS-022 · Redesign v2: login and campus home

- **Type:** feature
- **Priority:** P0
- **Estimate:** 90 min
- **Rubric / Spec:** feedback items 3, 4, 8, 9, *skeletons
- **Depends on:** none
- **Uses contract:** UPS-021
- **Related:** UPS-021, UPS-027
- **Paths:** web/src/features/auth/, web/src/features/home/
- **Freeze-Allowed:** no
- **Acceptance:**
  - Login shows "Tus clubs en un solo campus" with the transparent logo; clean white layout.
  - Campus home in the reference style (welcome + continue learning + upcoming events + latest posts), the same phrase in the hero; the "Explorar academias" and "Comunidad" buttons removed from the hero card.
  - `/clubes` lists the clubs (cards with logo and color); `/academias` redirects to `/clubes`. No "Academia" in visible text.
  - Skeletons that match each block's final shape.
- **Verify:** `npm --prefix web run lint && npm --prefix web run build && uv run pytest -q e2e`
- **Next step:** login copy and layout.

## UPS-023 · Redesign v2: club home and route catalog

- **Type:** feature
- **Priority:** P0
- **Estimate:** 120 min
- **Rubric / Spec:** feedback items 19, 20, 23
- **Depends on:** none
- **Uses contract:** UPS-021
- **Related:** UPS-021, UPS-024
- **Paths:** web/src/features/academy/
- **Freeze-Allowed:** no
- **Acceptance:**
  - Club home without the "Inscribirme" button and without "Continuar donde te quedaste"; one "Continúa aprendiendo" block with route cards.
  - Route catalog like the reference: colored cover tiles (club color + icon), title, progress line, "Iniciar / Continuar / Repasar" pill on the tile.
  - Skeletons per block; no "Academia" in visible text.
- **Verify:** `npm --prefix web run lint && npm --prefix web run build && uv run pytest -q e2e`
- **Next step:** route cards.

## UPS-024 · Redesign v2: dark course player, completion when the video ends

- **Type:** feature
- **Priority:** P0
- **Estimate:** 150 min
- **Rubric / Spec:** feedback items 25, 26 · player reference image
- **Depends on:** none
- **Uses contract:** UPS-021
- **Related:** UPS-007, UPS-023
- **Paths:** web/src/features/learning/
- **Freeze-Allowed:** no
- **Acceptance:**
  - The route and player pages use the dark course theme (`data-theme="dark"`), layout like the reference: top bar with "Ir a inicio", left sidebar (route title, % bar, search, collapsible modules with x/y and checks), video area, description and resources below.
  - No manual "Marcar como completada": the lesson is marked complete when the YouTube video ends (iframe `enablejsapi=1` + postMessage state from the youtube-nocookie origin, no external script, no CSP change); the UI shows the state and moves on. Messages from other origins are ignored.
  - Skeletons for sidebar and video; works at 390 px (drawer).
- **Verify:** `npm --prefix web run lint && npm --prefix web run build && uv run pytest -q e2e`
- **Next step:** postMessage listener with origin check.

## UPS-025 · Redesign v2: community fixes (hidden messages, 512 chars, one reaction, club-scoped)

- **Type:** feature
- **Priority:** P1
- **Estimate:** 150 min
- **Rubric / Spec:** feedback items 12, 13, 14, 16, 22
- **Depends on:** none
- **Uses contract:** UPS-021
- **Related:** UPS-011, UPS-018
- **Paths:** web/src/features/community/, app/routers/community.py, app/services/community.py, app/routers/reactions.py, app/services/reactions.py, app/tests/test_community.py, app/tests/test_reactions.py
- **Owned elsewhere (logged decision, owner UPS-002 integrated):** app/schemas/community.py (512-char limit, hidden flag), app/models/community.py + app/migrations/versions/0003_one_reaction_per_user.py (one reaction per user and post).
- **Freeze-Allowed:** no
- **Acceptance:**
  - The "Para publicar…" notice is gone.
  - Hidden posts/comments stay in place as "Mensaje oculto": the API sends a flag and no body, image or link (redacted server-side); no comments or reactions on hidden items.
  - Posts limited to 512 characters (schema → 422) with a live counter in the composer.
  - One reaction per account per post: reacting with another kind replaces the previous one; migration dedupes existing rows (tested on Postgres).
  - `/a/:slug/comunidad` shows the club channel inside the club layout (no jump to the campus theme).
  - Skeletons for channels and posts. Security review required.
- **Verify:** `uv run pytest -q app/tests/test_community.py app/tests/test_reactions.py && npm --prefix web run build && uv run pytest -q e2e`
- **Next step:** `test_hidden_post_is_redacted`.

## UPS-026 · Redesign v2: calendar day filter and copy

- **Type:** feature
- **Priority:** P1
- **Estimate:** 60 min
- **Rubric / Spec:** feedback items 17, 18
- **Depends on:** none
- **Uses contract:** UPS-021
- **Related:** UPS-013
- **Paths:** web/src/features/events/
- **Freeze-Allowed:** no
- **Acceptance:**
  - Clicking a day in the month view filters the list below to that day (clear filter button; keyboard accessible).
  - Subtitle: "Talleres, sesiones, hackatones y eventos en todos los clubes". No "Academia" in visible text. Skeletons.
- **Verify:** `npm --prefix web run lint && npm --prefix web run build`
- **Next step:** selected-day state.

## UPS-027 · Redesign v2: blog and gallery with demo content

- **Type:** feature
- **Priority:** P2
- **Estimate:** 150 min
- **Rubric / Spec:** feedback "Galería/Blog" · ipnprofes blog reference images
- **Depends on:** none
- **Uses contract:** UPS-021
- **Related:** UPS-017
- **Paths:** web/src/features/blog/, web/src/features/gallery/, app/fixtures/demo.json, app/seed.py, app/tests/test_seed.py, app/tests/test_academies.py, app/tests/test_admin.py, app/tests/test_blog.py, app/tests/test_gallery.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - Blog like the reference: title + subtitle, search, "Artículos en tendencia" row, category chips, featured article + card grid; read time from body length; no invented views/likes.
  - Gallery with project cards; empty states designed.
  - Seed adds demo projects and blog posts (`demo_data`), and the seed copy uses "club" (hero title "Tus clubs en un solo campus"); idempotent.
- **Verify:** `uv run pytest -q app/tests/test_seed.py && npm --prefix web run build`
- **Next step:** demo fixtures.

## UPS-028 · Redesign v2: "Club" terminology in the API and admin panels

- **Type:** feature
- **Priority:** P1
- **Estimate:** 90 min
- **Rubric / Spec:** feedback item 3
- **Depends on:** none
- **Uses contract:** UPS-021
- **Related:** UPS-008, UPS-009, UPS-014
- **Paths:** web/src/features/academy-admin/, web/src/features/superadmin/, web/src/features/account/, web/src/features/resources/, app/services/admin.py, app/services/events.py, app/services/academies.py, app/services/gallery.py, app/services/academy_admin.py, app/tests/test_permissions_matrix.py, docs/permissions-matrix.md
- **Freeze-Allowed:** no
- **Acceptance:**
  - Every user-visible "Academia/Academias" in API messages and in the panels says "Club/Clubes" (routes `/a/:slug`, models, API paths and `academy_id` stay).
  - Panels get skeletons and the v2 look.
- **Verify:** `uv run pytest -q && npm --prefix web run build`
- **Next step:** grep and replace messages.

## UPS-029 · Redesign v2: acceptance flow (e2e) updated to the new screens

- **Type:** test
- **Priority:** P0
- **Estimate:** 120 min
- **Rubric / Spec:** S001 flow steps 1–6 · `docs/acceptance.md`
- **Depends on:** UPS-021, UPS-022, UPS-023, UPS-024, UPS-026, UPS-028
- **Uses contract:** UPS-016
- **Related:** UPS-016, UPS-025, UPS-027
- **Paths:** e2e/, docs/acceptance.md
- **Freeze-Allowed:** no
- **Acceptance:**
  - The 6 steps pass on desktop and mobile against the v2 screens, with selectors by role and accessible name (no CSS classes): "Club/Clubes" labels, the club home "Continúa aprendiendo" tile instead of "Continuar: Clase 3 · 50 %", the shell nav and notifications instead of the provisional-password banner.
  - Step 3 completes the lesson the v2 way: the test dispatches the YouTube player "ended" state as a `message` event from the `https://www.youtube-nocookie.com` origin and the iframe as source (no network to YouTube), then checks progress 75 % after a reload. A second message from another origin changes nothing.
  - `docs/acceptance.md` screenshots and step descriptions match the v2 flow.
- **Verify:** `npm --prefix web run build && uv run pytest -q e2e`
- **Next step:** run e2e on main after the wave merges and fix step by step.

## UPS-030 · Free internet hosting: one container on Render, Postgres and uploads on Neon

- **Type:** ops
- **Priority:** P1
- **Estimate:** 180 min
- **Rubric / Spec:** decision 2026-10-08 (human): public deploy at zero cost with Render free + Neon free. Supabase was dropped: a free project pauses after 7 days without database activity, which would break every image.
- **Depends on:** UPS-015
- **Uses contract:** UPS-015
- **Related:** UPS-020
- **Paths:** app/services/media.py, app/models/media.py, app/models/__init__.py, app/migrations/versions/0004_media_objects.py, app/main.py, app/tests/test_media_storage.py, Dockerfile, deploy/entrypoint.sh, render.yaml, docs/deploy-render.md, .uak/OWNERS.md
- **Freeze-Allowed:** no
- **Acceptance:**
  - `MEDIA_STORAGE=database` stores uploads in a `media_objects` table (migration 0004, reversible) instead of the disk, because the free Render disk is wiped on every restart. Stored URLs stay `/media/<kind>/<name>`; `GET /media/...` serves them with the media CSP and a long immutable cache. `MEDIA_STORAGE=disk` (default) keeps today's behavior.
  - The last Dockerfile stage (`single`) serves the built SPA and the API from one container on `$PORT`; the compose targets (`api`, `web`) are unchanged.
  - `render.yaml` describes the free web service; `docs/deploy-render.md` walks through Neon and Render with free plans only, the first seed, and the limits (sleep after 15 min, Neon size, rate limit by IP behind the proxy).
  - Backend suite green with 100 % coverage; `docker build -t upiixsol-single .` builds and the container answers `/api/health` and the SPA.
- **Verify:** `uv run pytest -q app/tests/test_media_storage.py && docker build -t upiixsol-single .`
- **Next step:** implement the storage switch, the single stage, the blueprint and the guide.

## UPS-031 · Seed: unused seeded accounts follow SEED_DEFAULT_PASSWORD

- **Type:** fix
- **Priority:** P0
- **Estimate:** 30 min
- **Rubric / Spec:** incident 2026-10-08 on Render: the first SEED_DEFAULT_PASSWORD (generated by the blueprint) was replaced before anyone logged in, so nobody could sign in and there is no database access to reset it.
- **Depends on:** UPS-030
- **Uses contract:** -
- **Related:** UPS-020, UPS-030
- **Paths:** app/seed.py, app/tests/test_seed.py, docs/deploy-render.md, docs/runbook.md, .uak/OWNERS.md
- **Freeze-Allowed:** no
- **Acceptance:**
  - With SEED_ON_START=true, a seeded account that was never used (must_change_password and no password_changed_at) gets the current SEED_DEFAULT_PASSWORD; accounts whose password was changed or reset by an admin are never touched.
  - Running the seed twice with the same password changes nothing.
  - The deploy guide and runbook explain how to recover a lost first password.
- **Verify:** `uv run pytest -q app/tests/test_seed.py`
- **Next step:** implement in seed(), test, document.

## UPS-032 · Club colors really apply, three-color wordmark without a logo, configurable site brand

- **Type:** fix
- **Priority:** P0
- **Estimate:** 180 min
- **Rubric / Spec:** human request 2026-10-08 · audit docs/audit/2026-10-08/clubs.md (1–5), admin.md (3)
- **Depends on:** UPS-021
- **Uses contract:** UPS-004
- **Related:** UPS-033, UPS-036
- **Paths:** web/src/index.css, web/src/lib/theme.tsx, web/src/lib/brand.tsx, web/src/layouts/, web/src/features/home/, web/src/features/academy/, web/index.html, web/public/brand/, e2e/test_branding.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - A club's primary/secondary/accent colors are used by buttons, bars, links and cards inside `/a/{slug}` and on its cards (`@theme inline`, so `--color-*` resolve where `AcademyTheme` sets `--academy-*`); the identity live preview reacts to unsaved colors.
  - Without a logo, a club name is drawn as a wordmark: the letters before the first "x" in the primary color, that "x" in the secondary, the rest in the accent (a name without "x" uses the primary for all). Same component in the header, cards and switcher; the card no longer repeats the name; switcher initials differ between clubs and the button is ≥ 44 px.
  - Toasts (layouts/Notifications.tsx) never cover page actions (admin.md 3).
  - The campus name and logo come from one place (`web/src/lib/brand.tsx`, overridable with `VITE_SITE_NAME`, `VITE_SITE_LOGO`); without a logo the campus uses the same wordmark rule. `index.html` title follows it.
  - Browser test: a club created without a logo shows its three colors in the header wordmark and its primary on a button.
- **Verify:** `npm --prefix web run lint && npm --prefix web run build && uv run pytest -q e2e`
- **Next step:** switch the theme block to `@theme inline`, add the Wordmark, then the brand config.

## UPS-033 · Stable layout and motion: reserved error space, animated height, modal transitions, auth and account fixes

- **Type:** ux
- **Priority:** P0
- **Estimate:** 240 min
- **Rubric / Spec:** human request 2026-10-08 · audit docs/audit/2026-10-08/auth.md (all), admin.md (1, 4), learning.md (3), content.md (6)
- **Depends on:** UPS-021
- **Uses contract:** UPS-004
- **Related:** UPS-034, UPS-035, UPS-036, UPS-038
- **Paths:** web/src/components/, web/src/features/auth/, web/src/features/account/, web/src/lib/auth.tsx, web/DESIGN.md
- **Freeze-Allowed:** no
- **Acceptance:**
  - Shared primitives in `web/src/components/` (Motion): a form message slot that reserves its line (no shift when an error appears), an animated-height container, and enter/exit transitions for `Modal`/`Drawer`; all respect reduced motion. `web/DESIGN.md` documents when to use them.
  - `/login`: the card keeps its top position; switching Entrar ↔ Crear cuenta animates the height and fades the new fields in; errors never resize the card. Client validation for every required field; the rate-limit message says how long to wait.
  - `/cuenta`: field errors in Spanish (no raw validator text), status messages replace each other instead of piling up, disabled buttons explain why, the Seguridad tab does not grow per error.
  - Role guard: visiting a page the role cannot see redirects and the URL changes too. Opening a drawer does not auto-focus a text field on phones.
  - Browser test measures the login card box before/after an error and a tab switch (top unchanged, no jump).
- **Verify:** `npm --prefix web run lint && npm --prefix web run build && uv run pytest -q e2e`
- **Next step:** build the primitives, then apply them to auth and account.

## UPS-034 · Calendar, blog and gallery: correct day/month sync, loading states, drafts filter

- **Type:** fix
- **Priority:** P1
- **Estimate:** 150 min
- **Rubric / Spec:** audit docs/audit/2026-10-08/content.md (1–5, 7–10)
- **Depends on:** UPS-033
- **Uses contract:** UPS-033
- **Related:** UPS-026, UPS-027
- **Paths:** web/src/features/events/, web/src/features/blog/, web/src/features/gallery/, app/services/blog.py, app/services/gallery.py, app/routers/blog.py, app/routers/gallery.py, app/tests/test_blog.py, app/tests/test_gallery.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - Changing month, view or the drafts toggle never shows old data under the new heading (skeleton or animated swap); the selected day shows its events after a month change; `?dia=` keeps the visible month in sync; the day detail scrolls into view; the month grid keeps a fixed cell height.
  - "Ver borradores" shows only drafts (API filter tested); "Artículos en tendencia" is renamed or really measures something.
  - Field-level errors in the event modal; titles readable on phones.
- **Verify:** `uv run pytest -q app/tests/test_blog.py app/tests/test_gallery.py && npm --prefix web run build && uv run pytest -q e2e`
- **Next step:** fix the calendar state, then the loading swaps, then drafts.

## UPS-035 · Community: hidden images, long words, counters, channel switch, own deletes

- **Type:** fix
- **Priority:** P0
- **Estimate:** 210 min
- **Rubric / Spec:** audit docs/audit/2026-10-08/community.md (all) · UPS-025 security notes
- **Depends on:** UPS-033
- **Uses contract:** UPS-033
- **Related:** UPS-025
- **Paths:** web/src/features/community/, app/services/community.py, app/routers/community.py, app/services/media.py, app/tests/test_community.py, app/tests/test_media.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - Hiding a post makes its image unavailable to everyone but moderators (no public `/media` URL for a hidden post); test proves it.
  - Long words wrap (no horizontal scroll at 390 px); the comment counter matches the server after hide/publish/poll; switching channel keeps the layout (no collapse to skeleton, scroll handled); a post made while switching never lands in the wrong channel.
  - Composer errors use the reserved slot; hiding animates; reactions row keeps its width; comments paginate ("Ver más"); image picker shows focus and a preview.
  - Authors can delete their own posts and comments (API + UI, tested in the permissions matrix); a malformed image is a 422, never a 500.
  - Decide and document whether non-members may post in a club channel (default: members of the club and admins only).
- **Verify:** `uv run pytest -q app/tests/test_community.py app/tests/test_media.py && npm --prefix web run build && uv run pytest -q e2e`
- **Next step:** security fixes first (hidden image, 500), then layout, then delete.

## UPS-036 · Admin panels: club permission page, modal errors, user defaults

- **Type:** fix
- **Priority:** P1
- **Estimate:** 120 min
- **Rubric / Spec:** audit docs/audit/2026-10-08/admin.md (2, 4–7, 9)
- **Depends on:** UPS-033, UPS-032
- **Uses contract:** UPS-033
- **Related:** UPS-009, UPS-010
- **Paths:** web/src/features/superadmin/, web/src/features/academy-admin/, app/services/admin.py, app/tests/test_admin.py, docs/permissions-matrix.md, app/tests/test_permissions_matrix.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - An admin opening another club's panel gets a clear "no administras este club" page with a way back (no retry button on a 403).
  - Modal errors use the reserved slot (no jump); club cards use the UPS-032 wordmark; the superadmin row explains why it cannot deactivate itself.
  - New users get a unique default nickname; the permissions matrix also covers the club content/enrollment reads.
- **Verify:** `uv run pytest -q app/tests/test_admin.py app/tests/test_permissions_matrix.py && npm --prefix web run build`
- **Next step:** 403 page, then modal errors, then nickname and matrix.

## UPS-037 · Usage analytics: activity events in the database, ready for a dashboard

- **Type:** feature
- **Priority:** P1
- **Estimate:** 240 min
- **Rubric / Spec:** human request 2026-10-08: record what students do and use, in the DB for now, scalable to a dashboard later
- **Depends on:** UPS-002
- **Uses contract:** -
- **Related:** UPS-032
- **Paths:** app/models/analytics.py, app/models/__init__.py, app/migrations/versions/0005_activity_events.py, app/services/analytics.py, app/routers/analytics.py, app/main.py, app/tests/test_analytics.py, web/src/lib/analytics.ts, web/src/App.tsx, docs/analytics.md
- **Freeze-Allowed:** no
- **Acceptance:**
  - Append-only `activity_events` table (bigint id, occurred_at, user_id, academy_id, event name from an allowlist, subject type/id, small JSON properties, session id, client), indexed for time-range queries by event, user and club; no PII in properties.
  - Server records key actions without slowing requests (login, lesson progress/completion, post/comment/reaction, resource open, enrollment); `POST /api/analytics/events` accepts small batches of client events (page view, video play/pause/end, search) for signed-in users, validated and rate-limited.
  - The web tracker batches and flushes (`sendBeacon` on page hide), never blocks the UI, and does nothing when the API rejects it.
  - `docs/analytics.md`: event catalogue, example dashboard queries (active users per day, completion funnel per route, top resources), retention and how to move the stream to a warehouse later; privacy notice impact noted.
  - Tests for the endpoint (allowlist, size limits, auth), the server hooks and the migration (up/down on SQLite and Postgres).
- **Verify:** `uv run pytest -q app/tests/test_analytics.py && npm --prefix web run build`
- **Next step:** model + migration, then server hooks, then the client tracker and docs.

## UPS-038 · Learning player: smooth lesson change, search, drawer focus

- **Type:** ux
- **Priority:** P2
- **Estimate:** 90 min
- **Rubric / Spec:** audit docs/audit/2026-10-08/learning.md (all)
- **Depends on:** UPS-033
- **Uses contract:** UPS-033
- **Related:** UPS-024
- **Paths:** web/src/features/learning/
- **Freeze-Allowed:** no
- **Acceptance:**
  - Next/previous lesson keeps the layout (no full-page skeleton flash); the sidebar search keeps its text across lessons; "Sin coincidencias" appears once for the whole search; the video area shows a placeholder until the iframe loads.
- **Verify:** `npm --prefix web run lint && npm --prefix web run build && uv run pytest -q e2e`
- **Next step:** keep the shell mounted between lessons, then the search state.

## UPS-039 · Wave-1 follow-ups: plain wordmark, one site brand everywhere, privacy notice, rate-limit flag

- **Type:** fix
- **Priority:** P0
- **Estimate:** 90 min
- **Rubric / Spec:** human request 2026-10-08 (no dark outline around the wordmark letters) · review notes of UPS-032, UPS-033 and UPS-037
- **Depends on:** UPS-032, UPS-033, UPS-037
- **Uses contract:** UPS-032
- **Related:** UPS-020
- **Paths:** web/src/lib/brand.tsx, web/src/features/academy/, web/src/features/auth/, web/src/App.tsx, web/src/components/States.tsx, web/src/lib/notifications.tsx, web/DESIGN.md, app/ratelimit.py, app/tests/test_ratelimit.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - The wordmark letters are drawn in the plain brand colors, with no outline or text-shadow around them.
  - A club name that is one very long word does not overflow the club home greeting at 390 px.
  - The login screen, `App.tsx` and `States.tsx` take the site name, logo and mascot from `SITE` (lib/brand.tsx); no hardcoded "UpiixSol" left in web/src outside lib/brand.tsx.
  - The register privacy notice mentions usage analytics (docs/analytics.md).
  - DESIGN.md and lib/notifications.tsx describe the current compact toast position.
  - `RATELIMIT_ENABLED=false` really disables the limits (slowapi reads the env var as text and overrides the app setting today); test both values.
- **Verify:** `uv run pytest -q app/tests/test_ratelimit.py && npm --prefix web run lint && npm --prefix web run build && uv run pytest -q e2e`
- **Next step:** remove the outline, then the brand leftovers, then the flag.

## UPS-040 · Mobile pass: skeletons that match the content and phone layouts on every screen

- **Type:** ux
- **Priority:** P0
- **Estimate:** 240 min
- **Rubric / Spec:** human request 2026-10-09: the app looks odd on phones in many cases, above all the skeletons
- **Depends on:** UPS-035, UPS-039, UPS-041, UPS-043
- **Uses contract:** UPS-033
- **Related:** UPS-038
- **Paths:** web/src/components/, web/src/layouts/, web/src/index.css, web/src/features/home/, web/src/features/academy/, web/src/features/auth/, web/src/features/account/, web/src/features/community/, web/src/features/events/, web/src/features/blog/, web/src/features/gallery/, web/src/features/resources/, web/src/features/superadmin/, web/src/features/academy-admin/, e2e/test_mobile.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - Every loading state at 390 px uses a skeleton with the same shape, count and size as the content it replaces (cards, lists, headers, tabs): no jump when data arrives (measured box before/after ≤ 4 px) and no skeleton wider than the screen.
  - Every screen of the three roles at 390×844 and 360×740 (including tabs and modals): no horizontal scroll, no clipped text or buttons, touch targets ≥ 44 px, nothing hidden behind the bottom tab bar, spacing consistent with web/DESIGN.md.
  - `e2e/test_mobile.py` visits each route per role at 390 px and asserts no horizontal scroll and stable skeleton→content boxes; screenshots of before/after kept for review.
- **Verify:** `npm --prefix web run lint && npm --prefix web run build && uv run pytest -q e2e`
- **Next step:** audit every route at 390 px, then fix the shared Skeleton set and each screen.

## UPS-041 · Site brand editable in /admin: name, logo, mascot and colors without redeploying

- **Type:** feature
- **Priority:** P0
- **Estimate:** 180 min
- **Rubric / Spec:** human request 2026-10-09: there is nowhere to change the UpiixSol logo / axolotl; name and logo must be easy to swap
- **Depends on:** UPS-039
- **Uses contract:** UPS-032
- **Related:** UPS-040
- **Paths:** app/models/site.py, app/models/__init__.py, app/migrations/versions/0006_site_settings.py, app/services/site.py, app/routers/site.py, app/tests/test_site.py, app/tests/test_permissions_matrix.py, docs/permissions-matrix.md, web/src/lib/brand.tsx, web/src/App.tsx, web/src/features/superadmin/, e2e/test_site_brand.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - A singleton `site_settings` row (migration 0006, reversible) holds the site name, logo URL, mascot URL and the three wordmark colors; defaults equal today's UpiixSol brand.
  - `GET /api/site` is public (the login page needs it). Superadmins edit it with `PUT /api/admin/site` and upload the logo/mascot (PNG, WebP or safe SVG, same media rules as club logos), or remove them (no logo → three-color wordmark). Permissions matrix rows added.
  - The web loads the site brand before first paint (short timeout, falls back to the built-in defaults), so the campus header, login screen, mascot spots, document title and wordmark all use it. A superadmin's change shows without a redeploy.
  - `/admin` gets a "Marca del sitio" tab with live preview, upload/remove for the logo and the mascot, name and colors; errors use the reserved FormMessage.
  - Tests: API (public read, superadmin-only writes, uploads, removal) and an e2e that changes the name and removes the logo, then sees the wordmark on the login page.
- **Verify:** `uv run pytest -q app/tests/test_site.py app/tests/test_permissions_matrix.py && npm --prefix web run build && uv run pytest -q e2e`
- **Next step:** model + migration + API, then the web store and the admin tab.

## UPS-042 · Login centered in the viewport on desktop

- **Type:** ux
- **Priority:** P1
- **Estimate:** 45 min
- **Rubric / Spec:** human request 2026-11-11 with a screenshot at 1913×1000: the login block (brand column + card) sits at the top of the page and leaves the lower half empty.
- **Depends on:** -
- **Uses contract:** UPS-033
- **Related:** UPS-040, UPS-044
- **Paths:** web/src/features/auth/index.tsx, e2e/test_login_layout.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - From 1024 px wide, when the login block fits the viewport, it is centered vertically: the space above and below it differs by ≤ 16 px at 1280×800 and 1920×1000. It stays centered horizontally.
  - When the block is taller than the viewport (short windows, phones), it starts at the top with the current padding and scrolls; nothing is clipped and there is no horizontal scroll at 390 and 360 px.
  - The card keeps its top edge while messages appear (`e2e/test_layout_stability.py::test_login_card_keeps_top_and_size` stays green), on "Entrar" and "Crear cuenta".
  - `e2e/test_login_layout.py` measures the block at 1280×800, 1920×1000 and 390×844, and keeps screenshots.
- **Verify:** `npm --prefix web run lint && npm --prefix web run build && uv run pytest -q e2e/test_login_layout.py e2e/test_layout_stability.py`
- **Next step:** center the main grid with min-h-dvh + content-center only from lg, then the e2e.

## UPS-043 · Phone drawers slide in from their own side with the backdrop

- **Type:** bug
- **Priority:** P0
- **Estimate:** 60 min
- **Rubric / Spec:** human video 2026-11-10 on production (onrender.com, iPhone, 390 px): opening "Más" in the bottom tab bar, the panel is first painted against the LEFT edge without the dark backdrop, then jumps to its place on the right with the backdrop; closing slides it out without the backdrop. Same Drawer (web/src/components/Overlay.tsx) serves "Más" (side right, web/src/layouts/Shell.tsx) and the player's "Contenido" (side left).
- **Depends on:** -
- **Uses contract:** UPS-033
- **Related:** UPS-040, UPS-038
- **Paths:** web/src/components/Overlay.tsx, web/src/layouts/Shell.tsx, e2e/test_drawer_motion.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - At 390×844 and 360×740, opening "Más": on every animation frame the panel is anchored to the right edge or entering from it (its left edge never left of its final position), and the backdrop is visible from the first frame the panel shows until it is gone. Closing exits to the same side, never across the screen.
  - The same holds for a left drawer (the player's "Contenido"): it enters and exits on the left.
  - With reduced motion the panel appears and disappears in its final place, with the backdrop, in one frame.
  - Focus behavior from UPS-033 is unchanged (`test_drawer_does_not_focus_a_text_field_on_phones` stays green); Esc and the close button still close it.
  - `e2e/test_drawer_motion.py` samples the panel box and the backdrop opacity on each requestAnimationFrame while opening and closing (motion enabled), for both sides, plus one reduced-motion case.
- **Verify:** `npm --prefix web run lint && npm --prefix web run build && uv run pytest -q e2e/test_drawer_motion.py e2e/test_layout_stability.py`
- **Next step:** reproduce with a frame-sampling e2e (red), then fix the dialog's initial position/animation in Overlay.tsx.

## UPS-044 · Sign in with boleta or email; a boleta is never registered twice

- **Type:** feature
- **Priority:** P1
- **Estimate:** 120 min
- **Rubric / Spec:** human request 2026-11-11: members sign in with their boleta number. Decision (human, same day): one field "Boleta o correo", because seeded superadmins and club admins have no boleta and must keep signing in with their email.
- **Depends on:** UPS-042
- **Uses contract:** -
- **Related:** UPS-020
- **Paths:** app/schemas/users.py, app/services/auth.py, app/routers/auth.py, app/tests/test_auth.py, web/src/features/auth/index.tsx, web/src/lib/auth.tsx, e2e/test_flow.py, e2e/test_login_boleta.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - `POST /api/auth/login` takes `identifier` + `password`: exactly 10 digits → the account with that boleta; otherwise → the account with that email (lower-cased). Wrong boleta, wrong email and wrong password give the same error and status (no account enumeration); the 5/min/IP rate limit and the provisional-password rule (UPS-020) apply the same. The old `email` key keeps working during the transition.
  - The login form has one field "Boleta o correo" (autocomplete username) with a hint; a member signs in with boleta, and a superadmin or club admin with email.
  - Registration requires a 10-digit boleta that no other account uses: a second account with the same boleta and another email gets 409 and the message shows on the boleta field; two concurrent registrations with the same boleta create one account. Same rule when a superadmin creates a user.
  - Tests: API (boleta login, email login, enumeration-safe errors, rate limit, duplicate boleta 409 incl. concurrent) and an e2e that registers, signs out and signs in with the boleta; `e2e/test_flow.py::sign_in` uses the new field.
- **Verify:** `uv run pytest -q app/tests/test_auth.py && npm --prefix web run lint && npm --prefix web run build && uv run pytest -q e2e`
- **Next step:** schema + service with tests, then the form and the e2e helper.
