# TASKS · stateless backlog

State lives on the `claims` branch (`uak status`); this file holds only tasks. IDs are `UPS-NNN`.
Priority is `P0/P1/P2`. Type is `setup/contract/spike/feature/bug/integration/demo/docs`. Check the graph with `uak graph`.
Spec: `docs/specs/001-campus/spec.md` · Plan: `docs/specs/001-campus/plan.md` · Email (UPS-071…081): `docs/specs/003-correo/` · Product: `IDEA.md`. UI in Spanish (Mexico).
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
- **Depends on:** UPS-027
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
- **Depends on:** UPS-033, UPS-063
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
- **Depends on:** UPS-035, UPS-039, UPS-041, UPS-043, UPS-004, UPS-061
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

## UPS-045 · Lesson video segments in the API: start/end seconds, parse ?t=, embed with start/end

- **Type:** feature
- **Priority:** P0
- **Estimate:** 150 min
- **Rubric / Spec:** human brief `.uak/ruta-ia-videos.md` §3 (2026-11-10, long videos split into classes) · `docs/specs/002-ruta-ia-videos/spec.md` §Acceptance (segments) · `plan.md` §Design 1, §Data, §Contracts
- **Depends on:** None
- **Uses contract:** None
- **Related:** UPS-046, UPS-047, UPS-048
- **Paths:** app/models/learning.py, app/migrations/versions/0007_lesson_segments.py, app/services/youtube.py, app/services/academy_admin.py, app/services/learning.py, app/schemas/learning.py, app/tests/test_youtube.py, app/tests/test_academy_admin.py, app/tests/test_learning.py, app/tests/test_permissions_matrix.py, docs/spikes/youtube.md
- **Freeze-Allowed:** no
- **Tests:** test_parse_start_formats, test_parse_start_rejects_hostile, test_embed_url_with_segment, test_embed_url_without_segment_unchanged, test_lesson_segment_end_must_exceed_start, test_lesson_patch_segment_checks_stored_value, test_lesson_prefills_start_from_url, test_lesson_duration_from_segment, test_lesson_out_exposes_segment, test_segment_write_respects_academy_scope
- **Acceptance:**
  - Nullable `start_s` and `end_s` on `lessons`, from migration 0007 (reversible, `batch_alter_table`, CHECKs `start_s >= 0` and `end_s > COALESCE(start_s, 0)`), mirrored in the model.
  - `parse_start()` understands `t=850`, `t=850s`, `t=14m10s`, `t=1h2m3s` and `start=850`, in the query or the fragment. Anything else gives `None`. `extract_video_id` is unchanged.
  - `embed_url(id, start_s, end_s)` adds `start` and `end` only from validated ints. With no segment the URL is exactly the same as today.
  - Lesson create and PATCH accept `start_s`/`end_s` (bounds 0–86 400). `end_s ≤ start_s` returns 422 `invalid_segment` with a Spanish message, and a PATCH is checked against the stored value. When `start_s` is not sent and the pasted URL has `t=`, it is prefilled before the URL is canonicalized. `duration_min = ceil((end_s − start_s)/60)` when both exist.
  - `LessonOut` and `LessonAdminOut` expose `start_s` and `end_s`. No new permission rows; the matrix covers a scoped write with the new fields. Coverage stays at 100 %.
  - Before pushing, send `uak msg impact:UPS-045 --kind contract` (consumers: UPS-048, UPS-047).
- **Verify:** `uv run pytest -q app/tests/test_youtube.py app/tests/test_academy_admin.py app/tests/test_learning.py app/tests/test_permissions_matrix.py && uv run ruff check app && uv run alembic upgrade head && uv run alembic downgrade base`
- **Next step:** red tests for `parse_start` and `embed_url`, then migration and model, then admin save and lesson output.

## UPS-046 · Spike: verify and complete the UpiixIA video catalog

- **Type:** spike
- **Priority:** P0
- **Estimate:** 120 min
- **Rubric / Spec:** `docs/specs/002-ruta-ia-videos/spec.md` · human brief `.uak/ruta-ia-videos.md` §5 (catalog)
- **Depends on:** None
- **Uses contract:** None
- **Related:** UPS-047
- **Paths:** docs/spikes/ruta-ia-catalog.md
- **Freeze-Allowed:** no
- **Test-First:** no (research: the output is a verified document, not behavior)
- **Acceptance:**
  - `docs/spikes/ruta-ia-catalog.md` holds the §5 catalog of `.uak/ruta-ia-videos.md` as the source of truth, one row per lesson: module, title, URL, `start_s`, `end_s`, `lang`, `status`, and links.
  - Every `verificar` row is opened: its title, channel and availability are confirmed, or it is replaced and the reason noted. The "3Blue1Brown Español" dubbed URL is preferred when it exists (then `lang: es`).
  - Every `buscar` row gets a real YouTube URL (NumPy/pandas ES, Hugging Face course videos, RAG ES parts 1–2, Ollama ES) or a documented substitute.
  - Chapter timestamps are copied from the YouTube descriptions to split the Karpathy videos (module 5, 2–3 segments each) and "Deep Dive into LLMs" (module 7, 4 segments).
  - Module 9: an official NVIDIA Jetson video for the intro lesson, with the tutorials as links (spec open question 4).
  - Nothing unverified is marked `ok`. Every row records the date it was checked.
  - A human reviews the document in the PR (every link opened at least once).
- **Verify:** `test -s docs/spikes/ruta-ia-catalog.md && ! grep -nE '[|] *(verificar|buscar) *[|]' docs/spikes/ruta-ia-catalog.md`
- **Next step:** copy the §5 catalog, then go module by module starting with modules 2, 4 and 8.

## UPS-048 · Web: segmented embeds in the player and start/end in the lesson form

- **Type:** feature
- **Priority:** P0
- **Estimate:** 150 min
- **Rubric / Spec:** human brief `.uak/ruta-ia-videos.md` §3 · `docs/specs/002-ruta-ia-videos/spec.md` §Acceptance (segments) · `plan.md` §Design 1, §Risks
- **Depends on:** UPS-045
- **Uses contract:** UPS-045
- **Related:** UPS-047
- **Paths:** web/src/lib/types.ts, web/src/features/learning/youtube.ts, web/src/features/learning/Player.tsx, web/src/features/academy-admin/index.tsx, web/src/features/academy-admin/clock.ts, e2e/test_segments.py, docs/specs/002-ruta-ia-videos/plan.md
- **Freeze-Allowed:** no
- **Tests:** test_player_src_keeps_segment_params, test_admin_form_prefills_start_from_url, test_admin_form_rejects_end_before_start
- **Acceptance:**
  - `playerSrc()` merges its parameters into `embed_url` with `new URL()`, so a URL that already has `?start=&end=` keeps them and gets a single `?`.
  - "Ver en YouTube" adds `&t=<start_s>` when there is a start.
  - The admin lesson form has Inicio and Fin fields (`mm:ss` or `h:mm:ss`, labeled, with a hint). A pure helper (`clock.ts`) converts between that text and seconds. Pasting a URL with `t=` prefills an empty Inicio. API and client errors show in the reserved `FormMessage` without layout shift.
  - The lesson list in the panel shows the segment (for example `14:10–48:58`) next to the duration.
  - In a real browser, check whether the embed reports `ended` (state 0) when playback reaches `end`, and record the result in `docs/specs/002-ruta-ia-videos/plan.md` §Risks. If it does not, apply the fallback written there (record it with `uak decision`).
  - e2e at 1280 and 390 px: the admin saves a segment from a pasted `?t=` URL, the member's embed `src` carries `start` and `end` plus `enablejsapi`, and a simulated `ended` marks the lesson complete. `.uak-shots/UPS-048/` gets a `design-critic` SHIP.
- **Verify:** `npm --prefix web run lint && npm --prefix web run build && uv run pytest -q e2e/test_segments.py`
- **Next step:** red e2e for the embed `src`, fix `playerSrc`, then the form fields and `clock.ts`.

## UPS-047 · Seed the "De cero a LLMs" route for UpiixIA

- **Type:** feature
- **Priority:** P0
- **Estimate:** 120 min
- **Rubric / Spec:** human brief `.uak/ruta-ia-videos.md` §4 (load) and §5 (catalog; links come from `docs/spikes/ruta-ia-catalog.md` once UPS-046 lands) · `docs/specs/002-ruta-ia-videos/spec.md` §Acceptance (route content), open questions 1–5 · `plan.md` §Design 2
- **Depends on:** UPS-045, UPS-048, UPS-002, UPS-027 (integrated), UPS-031 (not yet integrated; it also writes app/seed.py, so this task starts after it)
- **Uses contract:** UPS-046
- **Related:** None
- **Paths:** app/fixtures/ruta-ia.json, app/seed.py, app/tests/test_seed_ruta_ia.py, e2e/test_ruta_ia.py, docs/runbook.md
- **Freeze-Allowed:** no
- **Tests:** test_ruta_ia_fixture_valid, test_ruta_ia_seed_creates_nine_modules, test_ruta_ia_seed_idempotent, test_ruta_ia_drafts_unless_ok, test_ruta_ia_never_edits_published_lesson, test_ruta_ia_language_suffix, test_ruta_ia_segment_duration, test_ruta_ia_keeps_demo_route
- **Acceptance:**
  - `app/fixtures/ruta-ia.json` holds the 9 modules from the UPS-046 catalog (whatever is verified at merge time), with `start_s`, `end_s`, `lang`, `status` and links per lesson. Every URL passes `extract_video_id`. `buscar` rows are left out.
  - `seed_ruta_ia(db)` runs inside `seed()`, outside the `has_content` guard. It matches route, module and lesson by title, creates what is missing, refreshes only still-unpublished lessons, never edits published lessons and never deletes. Two runs give the same counts.
  - The route is published. Lessons are published only when `status: ok`. Each description ends with the language suffix. `duration_min` comes from the segment. The old demo route is not touched (spec open question 1).
  - The seed prints a one-line summary. `docs/runbook.md` says how to run the content step in prod (human only).
  - e2e: a member opens lesson 1.2 "Variables"; the embed carries `start=2938&end=5665`; a simulated `ended` moves the route's progress bar.
- **Verify:** `uv run pytest -q app/tests/test_seed_ruta_ia.py app/tests/test_seed.py && uv run pytest -q e2e/test_ruta_ia.py`
- **Next step:** red fixture and idempotency tests, then the fixture from the spike, then `seed_ruta_ia`.

## UPS-049 · E2E on Windows: a locked e2e.db at teardown must not fail the next test

- **Type:** fix
- **Priority:** P2
- **Estimate:** 20 min
- **Rubric / Spec:** review of UPS-041/042/043 on Windows, 2026-11-11: `uv run pytest e2e` gave 8 failed + 18 errors on main (mobile tests of test_admin_panels and test_community). Cause: when the `site` fixture switches desktop → mobile, `workdir.cleanup()` raises `PermissionError [WinError 32]` on `e2e.db` (the server process still holds it) and pytest reports it in the setup of the first mobile test. That test never runs, and the next ones depend on its state ("still the superadmin on /admin?tab=usuarios"). Proven: with `ignore_cleanup_errors=True` the same run gives 79 passed, 1 skipped, 0 errors.
- **Depends on:** None
- **Uses contract:** None
- **Related:** UPS-016
- **Paths:** e2e/conftest.py
- **Freeze-Allowed:** no
- **Test-First:** no (test infrastructure: the proof is the full e2e run, not a new assertion)
- **Acceptance:**
  - The temporary directory of the `site` fixture ignores cleanup errors (`tempfile.TemporaryDirectory(..., ignore_cleanup_errors=True)`), after the server has been terminated and awaited. No test, assertion or skip changes.
  - On Windows, `uv run pytest e2e` shows 0 failed and 0 errors (before: 8 failed, 18 errors). Linux behavior is unchanged.
- **Verify:** `npm --prefix web run build && uv run pytest -q e2e`
- **Next step:** one-line change in `_start_server`, then the full e2e run.

## UPS-050 · SVG upload hardening: reject processing instructions and cap `<use>` fan-out

- **Type:** security
- **Priority:** P2
- **Estimate:** 60 min
- **Rubric / Spec:** security review of UPS-041 (PR #72), 2026-11-11, two LOW findings in code already on main. Contained today by `MEDIA_CSP` (`default-src 'none'; sandbox`) and `nosniff`; only a superadmin or club admin can upload.
- **Depends on:** None
- **Uses contract:** None
- **Related:** UPS-041, UPS-035
- **Paths:** app/services/media.py, app/tests/test_media.py
- **Freeze-Allowed:** no
- **Tests:** test_svg_rejects_processing_instruction, test_svg_rejects_use_fan_out, test_svg_plain_logo_still_accepted
- **Acceptance:**
  - `_svg_is_safe` rejects any processing instruction after the XML declaration (for example `<?xml-stylesheet ... href="https://evil.example/x.xsl"?>`), or the stored bytes are the sanitized serialization instead of the raw upload. Both uploads (club logo and site logo or mascot) get 422 as for other unsafe SVGs.
  - A SVG with more than a small fixed number of `<use>` elements (at most 20) or with nested `<use>`/`<symbol>` references is rejected with the same 422.
  - A normal logo SVG (paths, groups, gradients, one or two `<use>`) is still accepted, and PNG/WebP paths are untouched. Coverage of `app/` stays at 100 %.
- **Verify:** `uv run pytest -q app/tests/test_media.py app/tests/test_site.py && uv run ruff check app`
- **Next step:** red tests with the two payloads, then the check in `_svg_is_safe`.

## UPS-051 · QA permissions: full role matrix tested through the API

- **Type:** integration
- **Priority:** P0
- **Estimate:** 120 min
- **Rubric / Spec:** docs/PRUEBAS-CAMPUS.md §2 (ROL-01…07) and §14 (SEC-02); docs/permissions-matrix.md
- **Depends on:** None
- **Uses contract:** None
- **Related:** UPS-058
- **Paths:** app/tests/test_qa_permissions.py
- **Freeze-Allowed:** yes
- **Acceptance:**
  - Every `/admin/*` and academy-panel endpoint returns 403 for a `member` (ROL-01) and every superadmin-only endpoint returns 403 for an `academy_admin` (ROL-03); the superadmin gets 2xx on any academy (ROL-04).
  - Each row of the permissions matrix is asserted for the 3 roles (ROL-05); public payloads (`PublicUser`, post and comment authors) never carry email or boleta (ROL-06).
  - A role change applies on the next token refresh, with no stale permissions (ROL-07).
  - IDOR: swapping user or academy IDs in the URL or body to reach another user's or academy's data gives 403 or 404 (SEC-02).
  - Any mismatch found is opened as a new bug task or `uak followup`, never fixed inside this task.
- **Verify:** `uv run pytest -q app/tests/test_qa_permissions.py`
- **Next step:** list endpoints from the code map, then one parametrized test per matrix row.

## UPS-052 · QA learning and Player: progress, navigation and 100 % in the browser

- **Type:** integration
- **Priority:** P0
- **Estimate:** 120 min
- **Rubric / Spec:** docs/PRUEBAS-CAMPUS.md §4 (LRN-01…08)
- **Depends on:** None
- **Uses contract:** None
- **Related:** UPS-055
- **Paths:** e2e/test_qa_learning.py
- **Freeze-Allowed:** yes
- **Acceptance:**
  - Routes → module → lesson navigation respects the admin's order (LRN-01); the YouTube Player loads with its thumbnail (LRN-02).
  - Completing a lesson raises the route % and survives a reload; un-completing lowers it; completing every lesson shows 100 % and the route as finished (LRN-03…05).
  - Previous/next in the Player moves across lessons and modules (LRN-06).
  - Lesson markdown with `<script>` or `onerror` runs nothing (LRN-07); a visitor without a session is asked to log in and nothing is saved (LRN-08).
  - Bugs found become new tasks or `uak followup`.
- **Verify:** `npm --prefix web run build && uv run pytest -q e2e/test_qa_learning.py`
- **Next step:** reuse the e2e conftest fixtures; one test per LRN ID.

## UPS-053 · QA auth and session: refresh, logout, redirects and rate limit

- **Type:** integration
- **Priority:** P0
- **Estimate:** 90 min
- **Rubric / Spec:** docs/PRUEBAS-CAMPUS.md §1 (AUTH-01…07)
- **Depends on:** None
- **Uses contract:** None
- **Related:** UPS-051
- **Paths:** e2e/test_qa_auth.py
- **Freeze-Allowed:** yes
- **Acceptance:**
  - Each seed role logs in and lands on its home (AUTH-01); 5+ wrong passwords give a generic error, then 429 (AUTH-02).
  - An expired or removed access token is renewed silently by the refresh (AUTH-03); a refresh token reused after logout gets 401 (AUTH-05).
  - After logout, the browser Back button shows no private data (AUTH-04).
  - `/admin`, `/panel/academia` and `/cuenta` without a session redirect to `/login` and return to the original route after login (AUTH-06); F5 on any inner route keeps the session with no blank screen (AUTH-07).
  - Bugs found become new tasks or `uak followup`.
- **Verify:** `npm --prefix web run build && uv run pytest -q e2e/test_qa_auth.py`
- **Next step:** one test per AUTH ID with the seed accounts.

## UPS-054 · QA community, moderation and reactions

- **Type:** integration
- **Priority:** P1
- **Estimate:** 120 min
- **Rubric / Spec:** docs/PRUEBAS-CAMPUS.md §7 (COM-01…10) and §8 (REA-01…03)
- **Depends on:** None
- **Uses contract:** None
- **Related:** UPS-057
- **Paths:** e2e/test_qa_community.py, app/tests/test_qa_community.py
- **Freeze-Allowed:** yes
- **Acceptance:**
  - Feed, General and one channel per academy are listed (COM-01); posting follows enrollment rules: enrolled member yes, non-enrolled 403 with a "Unirme al club" offer, General open (COM-02…04).
  - Posts with an image, comments and deleting my own posts work (COM-05); hidden posts and comments vanish for members and their authors cannot delete them; a hidden image is 403 for members and visible to moderators (COM-06, COM-07).
  - Infinite scroll paginates with a cursor and no duplicates (COM-08); malicious HTML/JS is sanitized (COM-09); post spam hits 429 (COM-10).
  - Reacting and un-reacting moves the counter and survives a reload; a fast double click never duplicates; `GET /reactions/mine` marks mine as active (REA-01…03).
  - Bugs found become new tasks or `uak followup`.
- **Verify:** `uv run pytest -q app/tests/test_qa_community.py && npm --prefix web run build && uv run pytest -q e2e/test_qa_community.py`
- **Next step:** API tests for limits and idempotence, e2e for the visible flows.

## UPS-055 · QA academy panel and superadmin: CRUD, ordering, enrollments and analytics

- **Type:** integration
- **Priority:** P1
- **Estimate:** 150 min
- **Rubric / Spec:** docs/PRUEBAS-CAMPUS.md §5 (ADM-01…09) and §6 (SUP-01…06)
- **Depends on:** UPS-041
- **Uses contract:** None
- **Related:** UPS-052
- **Paths:** e2e/test_qa_admin.py
- **Freeze-Allowed:** yes
- **Acceptance:**
  - Route, module and lesson CRUD with delete confirmation; reordering persists on reload and matches the student side (ADM-01, ADM-02).
  - Branding shows live on `/a/:slug`; low-contrast colors warn or block per WCAG AA (ADM-03, ADM-04).
  - Enrollments, academy home, resources and events update everywhere they appear; analytics match the seed data (ADM-05…09).
  - Superadmin creates an academy with theme and channel without code, manages users (role, academy, password reset with no temporary password in logs), deactivates or edits academies (SUP-01…03).
  - Site brand edits show on login, home and header without redeploy; removing the logo or mascot falls back cleanly; user pagination over 50 rows has no duplicates or gaps (SUP-04…06).
  - Bugs found become new tasks or `uak followup`.
- **Verify:** `npm --prefix web run build && uv run pytest -q e2e/test_qa_admin.py`
- **Next step:** one test per ADM/SUP ID not already covered by e2e/test_admin_panels.py.

## UPS-056 · QA resources, events, account, blog and gallery

- **Type:** integration
- **Priority:** P1
- **Estimate:** 120 min
- **Rubric / Spec:** docs/PRUEBAS-CAMPUS.md §9 (RES, EVT), §10 (ACC) and §11 (BLG)
- **Depends on:** None
- **Uses contract:** None
- **Related:** UPS-058
- **Paths:** e2e/test_qa_content.py
- **Freeze-Allowed:** yes
- **Acceptance:**
  - A member downloads a resource with the right name and type (RES-01).
  - `/calendario` shows events from several clubs on the right date and time in America/Mexico_City; the home lists only upcoming events (EVT-01, EVT-02).
  - Nickname and avatar changes show in the header and my posts; email change asks for the current password (bad password errors, duplicate 409); a password change invalidates other sessions (ACC-01…03).
  - Blog and gallery CRUD with cover shows on list and detail pages; an unknown slug gives a friendly 404; rich-editor scripts are sanitized (BLG-01…04).
  - Bugs found become new tasks or `uak followup`.
- **Verify:** `npm --prefix web run build && uv run pytest -q e2e/test_qa_content.py`
- **Next step:** one test per ID not already covered by e2e/test_content.py.

## UPS-057 · QA mobile and accessibility: axe, palette contrast and keyboard

- **Type:** integration
- **Priority:** P1
- **Estimate:** 150 min
- **Rubric / Spec:** docs/PRUEBAS-CAMPUS.md §12 (MOB-01…04) and §13 (A11Y-01…05)
- **Depends on:** UPS-040
- **Uses contract:** None
- **Related:** UPS-054
- **Paths:** e2e/test_qa_mobile_a11y.py, docs/qa/a11y-report.md
- **Freeze-Allowed:** yes
- **Acceptance:**
  - At 375 px every route has no horizontal scroll, no clipped text and touch targets of 44 px or more; menu, ClubSwitcher and modals open, close and trap focus; Player and admin tables scroll inside their container; landscape does not break (MOB-01…04).
  - axe reports 0 serious violations on home, academy, Player, community, account and admin (A11Y-01); everything is reachable by keyboard with a visible focus (A11Y-02).
  - UpiixSol and UpiixIA palettes pass AA on a light background (4.5:1, or 3:1 for large text); `prefers-reduced-motion` removes large animations (A11Y-03, A11Y-04).
  - The manual NVDA check on login and Player is written in docs/qa/a11y-report.md (A11Y-05).
  - Bugs found become new tasks or `uak followup`.
- **Verify:** `npm --prefix web run build && uv run pytest -q e2e/test_qa_mobile_a11y.py`
- **Next step:** after UPS-040, run axe per route at 375 px and 1440 px.

## UPS-058 · QA security and uploads

- **Type:** integration
- **Priority:** P0
- **Estimate:** 120 min
- **Rubric / Spec:** docs/PRUEBAS-CAMPUS.md §14 (SEC-01…07), §9 (RES-02) and §10 (ACC-04); .uak/docs/SECURITY.md §Launch checklist
- **Depends on:** None
- **Uses contract:** None
- **Related:** UPS-051
- **Paths:** app/tests/test_qa_security.py
- **Freeze-Allowed:** yes
- **Acceptance:**
  - Extra JSON fields give 422 (SEC-01); passwords are stored as argon2id (SEC-06); 500 errors return the uniform JSON with no stack trace (SEC-07).
  - A fake-extension upload (a `.png` that is HTML or SVG with script) is rejected or re-encoded and never served as `text/html` (SEC-03); `.exe`, `.html` and files over 10 MB are rejected with a clear message (RES-02); a non-image or oversized avatar is rejected and images are re-encoded (ACC-04).
  - CORS answers only the `CORS_ORIGINS` origins and cookies carry `Secure`/`HttpOnly` where used (SEC-04).
  - `git grep` finds no secrets and `.env.example` holds no real values (SEC-05); the result is noted in the PR without printing any secret.
  - Bugs found become new tasks or `uak followup`.
- **Verify:** `uv run pytest -q app/tests/test_qa_security.py`
- **Next step:** one test per SEC ID, with crafted upload fixtures generated in the test.

## UPS-059 · QA staging deploy: Render + Neon checklist

- **Type:** integration
- **Priority:** P0
- **Estimate:** 120 min
- **Rubric / Spec:** docs/PRUEBAS-CAMPUS.md §15 (DEP-01…05) and §0 (P0-06, P0-07); docs/deploy-render.md; docs/runbook.md
- **Depends on:** UPS-031
- **Uses contract:** None
- **Related:** UPS-031
- **Paths:** docs/qa/staging-checklist.md
- **Freeze-Allowed:** yes
- **Acceptance:**
  - Migrations 0001…0006 go up, down to base and up again on SQLite and Postgres 16 (P0-06); a clean `docker compose up` with no volumes runs the seed and `/api/ready` answers ok (P0-07).
  - A clean staging deploy runs migrations by itself and `/api/health` and `/api/ready` answer ok (DEP-01); a cold start loads in under 60 s with no UI error (DEP-02).
  - Uploaded images survive a redeploy (DEP-03); deep links such as `/a/x/clases/1` serve the SPA on reload (DEP-04); Neon backup and restore follow the runbook (DEP-05).
  - Each check is recorded in docs/qa/staging-checklist.md with date, command and real result; deploying needs a human's authorization (agents create no accounts and spend nothing).
  - Bugs found become new tasks or `uak followup`.
- **Verify:** `uv run alembic upgrade head && uv run alembic downgrade base && uv run alembic upgrade head`
- **Next step:** run P0-06 and P0-07 locally, then ask the human to trigger the staging deploy.

## UPS-060 · QA load: how many concurrent users the campus supports

- **Type:** integration
- **Priority:** P1
- **Estimate:** 150 min
- **Rubric / Spec:** docs/deploy-render.md §Lo que implica el plan gratis (512 MB RAM, 0.1 CPU, Neon free); docs/PRUEBAS-CAMPUS.md §15
- **Depends on:** None
- **Uses contract:** None
- **Related:** UPS-059
- **Paths:** perf/locustfile.py, perf/run_local.sh, docs/qa/load-report.md
- **Freeze-Allowed:** yes
- **Acceptance:**
  - `perf/locustfile.py` models a realistic student mix with seed accounts: login and refresh, home, academy page, Player and marking a lesson done, community feed with infinite scroll, posting and reacting, calendar; plus a small share of academy admins. Locust runs through `uvx locust`, so pyproject.toml and uv.lock are not touched.
  - `perf/run_local.sh USERS DURATION` starts the app on `$UAK_PORT` with Postgres, runs Locust headless and exits non-zero if the error rate is over 1 % or p95 is over 1500 ms.
  - Rate limits (AUTH-02, COM-10) are not counted as capacity errors: test users are spread out, or the limit is raised only in the load environment and that is noted in the report.
  - A step ramp locally (10, 25, 50, 100, 200 users) is run, limited to 0.1 CPU and 512 MB with `docker run --cpus 0.1 --memory 512m`, to approximate Render free; the breaking point is the first step where p95 > 1500 ms or errors > 1 %.
  - docs/qa/load-report.md records, per step: users, RPS, p50, p95, error rate, RAM, slowest endpoints, and the conclusion "supports about N concurrent users on Render free + Neon free" with how it was measured. Numbers come only from real runs, never estimates.
  - The same ramp against staging runs only with a human's explicit authorization (it spends Neon quota and may wake or saturate Render); never against production.
  - Bottlenecks found (N+1 queries, missing indexes, images served from the database) become new tasks or `uak followup`, not fixes in this task.
- **Verify:** `bash perf/run_local.sh 20 60s`
- **Next step:** write the locustfile with seed accounts, then the local ramp with docker CPU/RAM limits.

## UPS-061 · Drawers and modals keep Tab focus inside until they close

- **Type:** bug
- **Priority:** P1
- **Estimate:** 45 min
- **Rubric / Spec:** found by UPS-057 (docs/PRUEBAS-CAMPUS.md MOB-02): at 375 px, tabbing through the open "Más" drawer moves focus out of the dialog (native `showModal()` lets Tab leave the page after the last control). Follow-up of UPS-043 (same component).
- **Depends on:** UPS-043
- **Uses contract:** UPS-033
- **Related:** UPS-057, UPS-040
- **Paths:** web/src/components/Overlay.tsx, e2e/test_overlay_focus.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - In any open drawer or modal, Tab from the last control goes to the first and Shift+Tab from the first goes to the last: a full lap plus two extra presses never leaves the dialog, at 375 px and 1280 px.
  - Escape and the close button still close it, and focus returns to the control that opened it.
  - Drawer motion (UPS-043) and first-field focus rules (UPS-033) are unchanged.
- **Verify:** `npm --prefix web run lint && npm --prefix web run build && uv run pytest -q e2e/test_overlay_focus.py e2e/test_drawer_motion.py e2e/test_layout_stability.py`
- **Next step:** red e2e that tabs through the "Más" drawer and the "Nuevo evento" modal, then a keydown trap in Overlay.tsx.

## UPS-062 · Remove DELETE /lessons/{id}/complete: a completed lesson stays completed

- **Type:** fix
- **Priority:** P1
- **Estimate:** 45 min
- **Rubric / Spec:** human decision 2026-11-12 (chat): a lesson is marked completed when the member watches the whole video and it stays that way; there is no UI and no API to unmark it. Found in review of UPS-052: LRN-04 of docs/PRUEBAS-CAMPUS.md ("Desmarcar la clase completada") contradicts it.
- **Depends on:** UPS-052
- **Uses contract:** None
- **Related:** UPS-007, UPS-010, UPS-052
- **Paths:** app/routers/learning.py, app/services/learning.py, app/services/progress.py, app/tests/test_learning.py, app/tests/test_analytics.py, app/tests/test_permissions_matrix.py, docs/permissions-matrix.md, docs/PRUEBAS-CAMPUS.md, e2e/test_qa_learning.py
- **Freeze-Allowed:** no
- **Tests:** test_uncomplete_endpoint_is_gone, test_completed_lesson_stays_completed, test_progress_never_goes_down
- **Acceptance:**
  - `DELETE /api/lessons/{id}/complete` no longer exists: the router, the `completed=False` branch of `set_completed` and `uncomplete_lesson` in progress.py are removed (no dead code). The call answers 405.
  - Completing twice still changes nothing, and a lesson never leaves the completed state; the route progress percentage never goes down.
  - The permission matrix test and docs/permissions-matrix.md drop the DELETE row. Tests that used DELETE to reset state (test_learning.py, test_analytics.py, the LRN-04 e2e) set up their state another way or assert there is no way to unmark.
  - LRN-04 in docs/PRUEBAS-CAMPUS.md is rewritten: "una clase completada no se puede desmarcar" (the Player offers no control for it).
  - A member who completed lessons before this change keeps them completed; no migration.
- **Verify:** `uv run pytest -q app/tests/test_learning.py app/tests/test_analytics.py app/tests/test_permissions_matrix.py`
- **Next step:** red test that DELETE answers 405, then remove the endpoint and the dead code, then fix the tests that used it.

## UPS-063 · Uploaded WebP images are served as image/webp on every OS

- **Type:** bug
- **Priority:** P1
- **Estimate:** 30 min
- **Rubric / Spec:** found by the UPS-056 review (david-3, Windows): with `MEDIA_STORAGE=disk` (the default) `/media/*.webp` is served as `application/octet-stream`. Starlette's `StaticFiles` guesses the type with Python's `mimetypes`, whose built-in table has no `.webp` before Python 3.13; macOS and desktop Linux add it from the OS, Windows (registry without it) and likely `python:3.12-slim` (no `/etc/mime.types`, unverified) do not. With `nosniff`, browsers may refuse those avatars, covers and post images. `MEDIA_STORAGE=database` (Render) is not affected.
- **Depends on:** -
- **Uses contract:** -
- **Related:** UPS-056, UPS-058
- **Paths:** app/services/media.py, app/tests/test_media.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - The app registers `image/webp` for `.webp` (and keeps `image/svg+xml` for `.svg`) when media is loaded, so `GET /media/<kind>/<name>.webp` answers `Content-Type: image/webp` with disk storage even when the OS mime table lacks it.
  - A test resets `mimetypes` to Python's built-in table (no OS files) and still gets `image/webp` for a stored WebP; `nosniff` and the media CSP stay.
- **Verify:** `uv run pytest -q app/tests/test_media.py && uv run ruff check app`
- **Next step:** red test with `mimetypes.init(files=[])`, then register the types in app/services/media.py.

## UPS-064 · Alert color: clubs without color_accent_2 show errors and delete buttons in green

- **Type:** fix
- **Priority:** P1
- **Estimate:** 30 min
- **Rubric / Spec:** design-critic of UPS-048 (P1-1), human accepted it as a followup on 2026-11-12: on UpiixIA a validation error reads as success. `web/src/lib/theme.tsx:82` sets `--academy-accent-2` to `safeColor(branding.color_accent_2, secondary)`; a club with `color_accent_2` null falls back to its secondary color (green #04944F on UpiixIA, 3.92:1 on white, fails AA). Every consumer of `accent-2` in web/ is an alert (FormMessage error, Field aria-invalid border, States alert, Badge alert, delete buttons in community, events and resources), and the campus default is the alert red #B4422F (5.58:1, `SITE.colors.accent2`).
- **Depends on:** UPS-048
- **Uses contract:** None
- **Related:** UPS-048, UPS-032
- **Paths:** web/src/lib/theme.tsx, web/src/lib/theme.test.ts, e2e/test_theme_alert.py
- **Freeze-Allowed:** no
- **Tests:** test_accent2_falls_back_to_alert_red, test_accent2_keeps_a_club_color, test_error_message_is_red_on_upiixia
- **Acceptance:**
  - When a club has no `color_accent_2`, `--academy-accent-2` is the site alert red (`SITE.colors.accent2`), never the club secondary color. A club that sets `color_accent_2` keeps it (after `safeColor`).
  - On UpiixIA, the invalid-field border and the FormMessage error are red and meet 4.5:1 on the light surface; checked in a real browser at 1280 and 390 wide, with a screenshot in `.uak-shots/`.
  - No other color token changes: the secondary color of every club is untouched.
- **Verify:** `npm --prefix web run build && uv run pytest -q e2e/test_theme_alert.py`
- **Next step:** red test that UpiixIA shows a red error on the lesson form, then change the fallback on theme.tsx:82.

## UPS-065 · Home shows the superadmin's hero title (saved, never rendered)

- **Type:** fix
- **Priority:** P2
- **Estimate:** 30 min
- **Rubric / Spec:** review of UPS-055 (PR #94, rejected 2026-11-12). `PUT /api/admin/home` saves `hero_title` (superadmin tab "Página principal", field "Título principal") and `GET /api/home` returns it in `hero.hero_title`, but `web/src/features/home/index.tsx` renders only `hero_text` (`heroText`, line 313). `test_sup05_home_text_shows_on_home` in e2e/test_qa_admin.py documents the gap.
- **Depends on:** None
- **Uses contract:** None
- **Related:** UPS-055
- **Paths:** web/src/features/home/index.tsx, e2e/test_qa_admin.py
- **Freeze-Allowed:** no
- **Tests:** test_sup05_home_title_shows_on_home
- **Acceptance:**
  - The superadmin's `hero_title` shows on the home hero at 1280 and 390 wide. An empty `hero_title` renders no empty heading.
  - `test_sup05_home_title_shows_on_home` asserts the title is visible; the existing hero_text assertion stays.
  - The hero keeps its reserved lines while /home loads (no layout jump, see DESIGN.md).
- **Verify:** `npm --prefix web run build && uv run pytest -q e2e/test_qa_admin.py`
- **Next step:** red: assert the title on the home in test_sup05, then render it in the hero.

## UPS-067 · Backend test: the temporary password never reaches the server log

- **Type:** test
- **Priority:** P2
- **Estimate:** 30 min
- **Rubric / Spec:** review of UPS-055: SUP-02 asks that the temporary password "no se muestra en logs". The e2e run cannot read server output (e2e/conftest.py sends uvicorn stdout and stderr to DEVNULL), so the server-side check belongs in the backend tests. Today `reset_password` in app/services/admin.py returns the password and has no logger call; this test keeps it that way.
- **Depends on:** None
- **Uses contract:** None
- **Related:** UPS-055
- **Paths:** app/tests/test_admin.py
- **Freeze-Allowed:** no
- **Tests:** test_reset_password_never_logs_the_temporary_password
- **Acceptance:**
  - With `caplog` at DEBUG, `POST /api/admin/users/{id}/reset-password` answers 200 with the password in its body, and the password appears in no log record (`caplog.text`).
  - The test passes on today's code. Prove it can fail: log the password in a scratch change, see the red, then drop that change (never committed).
- **Verify:** `bash .uak/bin/q uv run pytest -q app/tests/test_admin.py -k reset_password`
- **Next step:** write the caplog test next to test_reset_password, then the scratch check.

## UPS-068 · PROPOSAL, needs human approval: academy analytics (ADM-09) has no screen or endpoint

- **Type:** feature
- **Priority:** P3
- **Estimate:** 120 min
- **Rubric / Spec:** PROPUESTA: a human picks one option before work starts. (a) `GET /api/academies/{slug}/analytics` for academy admins plus an "Analíticas" tab in `/panel/academia` (a new screen is scope). (b) Keep ADM-09 a backend-only check (app/tests/test_analytics.py) and mark it as not e2e in `docs/PRUEBAS-CAMPUS.md`. Evidence: ADM-09 ("Los números cuadran con los datos del seed", marked ❌). `app/routers/analytics.py` only has `POST /api/analytics/events` (ingest). Found in review of UPS-055.
- **Depends on:** None
- **Uses contract:** None
- **Related:** UPS-055
- **Paths:** app/routers/analytics.py, app/services/analytics.py, app/tests/test_analytics.py, web/src/features/academy-admin/index.tsx, e2e/test_qa_admin.py, docs/PRUEBAS-CAMPUS.md
- **Freeze-Allowed:** no
- **Tests:** test_academy_analytics_match_seed (option a only)
- **Acceptance (after human picks the option):**
  - Option (a): the panel numbers equal the seed counts from the same query the backend test uses, at 1280 and 390 wide.
  - Option (b): ADM-09 in docs/PRUEBAS-CAMPUS.md names app/tests/test_analytics.py as its check and says it is not e2e.
- **Verify:** `npm --prefix web run build && uv run pytest -q e2e/test_qa_admin.py app/tests/test_analytics.py`
- **Next step:** human picks (a) or (b); then the red test.

## UPS-069 · e2e LRN-02: the fake YouTube embed answers like the real one

- **Type:** bug
- **Priority:** P1
- **Estimate:** 20 min
- **Rubric / Spec:** `e2e/test_qa_learning.py::test_player_loads_the_video_with_its_thumbnail` is red on main (desktop and mobile) since UPS-048: the Player now shows the video only once the embed answers over `postMessage` (a blocked embed still fires `onLoad`), and this test's fake embed never posts anything, so "Cargando video" stays. Found while verifying UPS-064; it fails the same with or without UPS-064. The product behavior is right; the test fixture is stale.
- **Depends on:** UPS-052
- **Uses contract:** UPS-048
- **Related:** UPS-048, UPS-062
- **Paths:** e2e/test_qa_learning.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - The fake embed in e2e/test_qa_learning.py posts a YouTube-like state message to the page (as e2e/test_segments.py does), so LRN-02 sees the iframe shown and "Cargando video" gone, at 1280 and 390.
  - No assertion of LRN-01…08 is weakened: only the fake embed changes.
- **Verify:** `npm --prefix web run build && uv run pytest -q e2e/test_qa_learning.py`
- **Next step:** make the FAKE_EMBED post an `infoDelivery` message to its parent, then run the module twice.

## UPS-070 · Unique nicknames, reserved "admin" and "upiixia", and admins delete comments

- **Type:** feature
- **Priority:** P1
- **Estimate:** 120 min
- **Rubric / Spec:** human request 2026-11-16. Today `users.nickname` has no unique constraint (test_admin.py says "nicknames are not unique, only the defaults avoid repeats"), `register_member` and `PATCH /api/account/profile` accept any nickname, and `DELETE /api/comments/{id}` is author only (docs/permissions-matrix.md: "moderators hide instead"). The human wants: no two users share a nickname; nobody takes "admin" or "upiixia"; an admin can delete comments. Nickname identity = casefold, accents removed, only letters and digits ("Admin", "a.d.min", "ÚPIIXIA" all collide with the reserved names). The rules live in a new `app/services/nicknames.py`, so `app/schemas/` and `app/models/user.py` (owned rows) stay untouched; the unique index is `lower(nickname)` created in a migration. "Admin" for comments = whoever `_can_moderate` already accepts: superadmin anywhere, academy_admin in channels of their own academy; a member still deletes only their own.
- **Depends on:** None
- **Uses contract:** None
- **Related:** UPS-062
- **Paths:** app/services/nicknames.py, app/services/auth.py, app/services/admin.py, app/services/account.py, app/services/community.py, app/migrations/versions/0008_unique_nickname.py, app/tests/test_nicknames.py, app/tests/test_community.py, app/tests/test_admin.py, app/tests/test_permissions_matrix.py, docs/permissions-matrix.md, web/src/features/community/Comments.tsx
- **Freeze-Allowed:** no
- **Tests:** test_register_rejects_a_taken_nickname_case_insensitive, test_register_default_nickname_is_numbered_when_taken, test_reserved_nicknames_are_refused_everywhere, test_profile_update_rejects_taken_and_reserved_nickname, test_migration_renames_existing_duplicate_and_reserved_nicknames, test_admin_deletes_any_comment_in_their_channel, test_admin_cannot_delete_comments_of_another_academy, test_member_cannot_delete_someone_elses_comment
- **Acceptance:**
  - Register, `POST /api/admin/users`, `PATCH /api/admin/users/{id}` and `PATCH /api/account/profile` answer 409 (`nickname_taken`, message in Spanish) when another user already has that nickname ignoring case; keeping your own nickname is not a conflict.
  - Same four endpoints answer 422 (`nickname_reserved`) for "admin" and "upiixia" in any casing, with accents or separators; automatic nicknames skip them the way they skip taken ones ("admin" becomes "admin2"). The seed accounts keep working.
  - Automatic nicknames are unique on register too (`register_member` reuses the numbering of `_unique_nickname`); a concurrent insert is a 409, never a 500 (the index backs it up).
  - Migration 0008 renames existing duplicates (oldest keeps the name; the rest get 2, 3…) and any reserved nickname, then creates the unique index on `lower(nickname)`; it round-trips (`alembic upgrade head && alembic downgrade base`) on SQLite and PostgreSQL 16.
  - `DELETE /api/comments/{id}` accepts the author, a superadmin and the academy_admin of the channel's academy; others get 403. The post's comment count stays right; hide keeps working. The matrix row and docs/permissions-matrix.md change from AUTHOR to the moderator set.
  - Comments.tsx shows the delete button to those moderators too, with the confirm text it uses today; 1280 and 390 wide.
  - Existing tests that state the old rules change only where the rule changed: test_admin.py::test_default_nickname_is_unique (line "A chosen nickname is kept as is") and the DELETE comments row of test_permissions_matrix.py. A human runs `uak allow UPS-070 --tests --reason 'nickname unique and admin delete comment, human request'` before those edits.
- **Verify:** `bash .uak/bin/q uv run pytest -q --tb=short -x app/tests/test_nicknames.py app/tests/test_community.py app/tests/test_admin.py app/tests/test_permissions_matrix.py app/tests/test_account.py app/tests/test_auth.py && uv run alembic upgrade head && uv run alembic downgrade base && npm --prefix web run build`
- **Next step:** write the stubs for the Tests names and `uak red UPS-070`; then app/services/nicknames.py, then the migration, then delete_comment.

## UPS-071 · Spike: Mailgun batch sending, unsubscribe header variables and webhook signature (test mode)

- **Type:** spike
- **Priority:** P1
- **Estimate:** 90 min
- **Rubric / Spec:** `docs/specs/003-correo/spec.md`, `plan.md` §Design (batch sending), ADR 0002. Human owner: victor.
- **Depends on:** None
- **Uses contract:** None
- **Related:** UPS-073, UPS-077
- **Paths:** docs/spikes/mailgun.md, app/tests/fixtures/mailgun/
- **Freeze-Allowed:** no
- **Test-First:** no (research: the output is a verified document and recorded payloads, not behavior)
- **Acceptance:**
  - `docs/spikes/mailgun.md` answers, each with the doc URL and date it was checked, or the request/response of a run with `o:testmode=yes`: the messages endpoint and auth for US and EU; the max recipients per call; whether `%recipient.*%` variables are substituted inside a custom `h:List-Unsubscribe` header (if not, which fallback of plan §Design applies); how `List-Unsubscribe-Post` is sent; `o:tracking`, `v:` user variables and how they come back in events.
  - The webhook section documents the payload of `delivered`, `failed` (permanent and temporary), `complained` and `unsubscribed`, and the signature fields (`timestamp`, `token`, `signature`) with the exact HMAC recipe.
  - `app/tests/fixtures/mailgun/` holds one JSON sample per event, with the addresses replaced by `@example.com`, and a recorded messages-API response (success and 4xx).
  - Any real call uses victor's key from `.env` (never printed or committed) and test mode only. Without a key, the spike stays docs-only and marks those answers "unverified".
- **Verify:** `bash .uak/bin/q bash -c 'test -s docs/spikes/mailgun.md && grep -q List-Unsubscribe docs/spikes/mailgun.md && ls app/tests/fixtures/mailgun/*.json'`
- **Next step:** read Mailgun's sending and webhook docs, write the questions as headings, then fill them.

## UPS-072 · Contract: mail tables, migration 0009, mail settings and the transport interface

- **Type:** contract
- **Priority:** P1
- **Estimate:** 180 min
- **Rubric / Spec:** `docs/specs/003-correo/plan.md` §Data and migrations, §Contracts (settings), ADR 0002. Human owner: victor.
- **Depends on:** UPS-070, UPS-002
- **Uses contract:** None
- **Related:** UPS-073, UPS-074, UPS-075, UPS-076, UPS-077
- **Paths:** app/models/mail.py, app/models/__init__.py, app/migrations/versions/0009_mail.py, app/config.py, .env.example, app/services/mailer.py, app/tests/test_mail_contract.py, web/src/lib/types.ts
- **Freeze-Allowed:** no
- **Tests:** test_mail_migration_round_trips, test_recipient_email_is_unique_per_campaign, test_suppression_is_keyed_by_normalized_email, test_prod_requires_mailgun_settings_when_mail_enabled, test_mail_disabled_by_default, test_console_transport_logs_count_without_addresses, test_unsubscribe_token_is_random_and_only_its_hash_is_stored, test_normalize_email_lowercases_and_trims
- **Acceptance:**
  - `app/models/mail.py`: `MailCampaign`, `MailRecipient`, `MailSuppression` with the columns, statuses and indexes of plan §Data, registered in `app/models/__init__.py`. `app/models/user.py` and `app/schemas/` are not touched.
  - Migration `0009_mail` (down_revision `0008_unique_nickname`) only creates the three tables; `alembic upgrade head && alembic downgrade base` is green on SQLite and on PostgreSQL 16 in CI.
  - `app/config.py` + `.env.example`: every setting of plan §Contracts with its default; `ENV=prod` + `MAIL_ENABLED=true` + `MAIL_BACKEND=mailgun` without `MAILGUN_API_KEY`, `MAILGUN_DOMAIN` or `MAILGUN_WEBHOOK_SIGNING_KEY` fails at startup with a clear message; secrets never appear in `repr` or errors.
  - `app/services/mailer.py`: `MailMessage`, `MailRecipientVars`, `BatchResult`, the `MailTransport` protocol, `ConsoleTransport` (logs subject length and recipient count, no addresses), `get_mail_transport()` dependency, `normalize_email()`, `new_unsubscribe_token() -> (token, sha256_hex)`.
  - `web/src/lib/types.ts` mirrors `Audience`, `Campaign`, `MailStatus`, `MailPreferences` of plan §Contracts.
- **Verify:** `bash .uak/bin/q uv run pytest -q --tb=short -x app/tests/test_mail_contract.py && uv run alembic upgrade head && uv run alembic downgrade base && npm --prefix web run build`
- **Next step:** stubs for the Tests names and `uak red UPS-072`; then the models, then the migration, then the settings.

## UPS-073 · Mailgun transport: batches of 1 000, recipient variables, test mode and safe errors

- **Type:** feature
- **Priority:** P1
- **Estimate:** 150 min
- **Rubric / Spec:** `docs/specs/003-correo/plan.md` §Design, `docs/spikes/mailgun.md` (UPS-071). Human owner: victor.
- **Depends on:** UPS-071, UPS-072
- **Uses contract:** None
- **Related:** UPS-075
- **Paths:** app/services/mailgun.py, app/tests/test_mailgun.py
- **Freeze-Allowed:** no
- **Tests:** test_one_call_per_batch_of_at_most_1000, test_each_recipient_gets_only_their_address, test_recipient_variables_carry_name_and_unsubscribe_url, test_list_unsubscribe_headers_are_sent, test_tracking_off_and_campaign_id_variable, test_test_mode_flag_sets_o_testmode, test_us_and_eu_base_urls, test_4xx_and_timeout_become_failed_batch_without_secrets, test_api_key_never_in_logs_or_errors
- **Acceptance:**
  - `MailgunTransport.send_batch` posts to `{MAILGUN_API_BASE}/v3/{MAILGUN_DOMAIN}/messages` with basic auth `api:<key>`, `from`, optional `h:Reply-To`, `to` = the batch, `recipient-variables` JSON, `subject`, `html`, `text`, `o:tracking=no`, `v:campaign_id`, `o:testmode` when enabled, and the unsubscribe headers as the spike settled.
  - More than 1 000 recipients are split into ordered batches; each call's result maps to `accepted` with the provider message id, or `failed` with a short error code.
  - Timeout 10 s; a 4xx/5xx or a timeout returns a failed `BatchResult` whose message has neither the key nor any address. Tests use `httpx.MockTransport` with the UPS-071 fixtures; no network.
- **Verify:** `bash .uak/bin/q uv run pytest -q --tb=short -x app/tests/test_mailgun.py`
- **Next step:** stubs for the Tests names and `uak red UPS-073`; then the request builder, then batching, then errors.

## UPS-074 · Mail audience: preview count and recipient search, scoped by role and club

- **Type:** feature
- **Priority:** P1
- **Estimate:** 240 min
- **Rubric / Spec:** `docs/specs/003-correo/spec.md` §Audiences and permissions, `plan.md` §Contracts, §STRIDE (elevation, disclosure). Human owner: victor.
- **Depends on:** UPS-072
- **Uses contract:** None
- **Related:** UPS-075, UPS-078
- **Paths:** app/services/mail_audience.py, app/routers/mail_audience.py, app/tests/test_mail_audience.py, app/tests/test_permissions_matrix.py, docs/permissions-matrix.md
- **Freeze-Allowed:** no
- **Tests:** test_all_counts_active_users_once, test_academy_counts_enrollees_and_its_admins, test_role_counts_that_role_only, test_individual_mixes_users_and_outside_addresses, test_individual_over_50_entries_or_20_emails_is_422, test_invalid_outside_address_is_422, test_excludes_inactive_suppressed_and_blocked_domains, test_academy_admin_cannot_mail_all, test_academy_admin_cannot_mail_a_role, test_academy_admin_cannot_mail_another_club, test_academy_admin_cannot_pick_a_non_enrolled_user, test_academy_admin_can_pick_a_co_admin_of_their_club, test_academy_admin_can_add_outside_addresses, test_recipient_search_hides_email_from_academy_admin, test_member_and_anon_get_403_and_401, test_mail_status_reports_quota_from_the_db
- **Acceptance:**
  - `resolve_audience(db, sender, audience) -> list[ResolvedRecipient]` and `preview()` implement spec §Audiences; the club scope comes from the DB (`users.academy_id`, `enrollments`), never from the body.
  - `GET /api/mail/status`, `POST /api/mail/audience/preview` and `GET /api/mail/recipients?q=` (cursor page ≤ 50; email only for superadmin) answer as plan §Contracts; schemas live in the service module.
  - The preview endpoint has a matrix row (OWN with `{kind: "academy", academy_id: world.academy_id}`); `recipients` and `status` are in the read matrix; `docs/permissions-matrix.md` is regenerated. Payload-dependent 403s are in `test_mail_audience.py`.
  - Preview p95 < 300 ms on the seeded data (one timing test, like the existing ones).
  - Human 2026-11-17 (victor): a club admin may also pick the co-admins of their own club in `individual` and in the recipient search; the preview count of typed outside addresses may exceed the final list for club admins (accepted, no oracle).
- **Verify:** `bash .uak/bin/q uv run pytest -q --tb=short -x app/tests/test_mail_audience.py app/tests/test_permissions_matrix.py`
- **Next step:** stubs for the Tests names and `uak red UPS-074`; then `resolve_audience`, then the router, then the matrix rows.

## UPS-075 · Mail campaigns: template, test send, draft → confirm → send in the background, quota, history

- **Type:** feature
- **Priority:** P1
- **Estimate:** 360 min
- **Rubric / Spec:** `docs/specs/003-correo/spec.md` §Composing and sending, §History, `plan.md` §Design, §Contracts, §STRIDE (tampering, repudiation, DoS). Human owner: victor.
- **Depends on:** UPS-074
- **Uses contract:** UPS-073
- **Related:** UPS-078, UPS-079
- **Paths:** app/services/mail_template.py, app/services/mail_campaigns.py, app/routers/mail_campaigns.py, app/tests/test_mail_campaigns.py, app/tests/test_mail_template.py, app/tests/test_permissions_matrix.py, docs/permissions-matrix.md
- **Freeze-Allowed:** no
- **Tests:** test_body_html_is_escaped_and_urls_become_links, test_subject_with_newline_is_422, test_template_uses_site_brand_and_public_base_url, test_footer_says_why_you_got_it, test_test_send_goes_only_to_the_sender, test_create_campaign_freezes_recipients_as_draft, test_confirm_twice_sends_once, test_batches_are_sent_in_the_background, test_failed_batch_marks_partial_and_keeps_others, test_resume_sends_only_pending, test_quota_exceeded_is_422_before_sending, test_rate_limit_6th_campaign_is_429, test_mail_disabled_answers_503, test_history_scoped_by_club_for_academy_admin, test_history_shows_sender_and_counts, test_send_logs_have_no_addresses
- **Acceptance:**
  - `mail_template.render(subject, body, footer_reason)` → `(html, text)`: body escaped, paragraphs, `<br>`, links only through `safe_url`; the layout carries the site name and logo (`SiteSettings`) with absolute URLs from `PUBLIC_BASE_URL` and the unsubscribe link `/baja?t=%recipient.unsubscribe_token%` (or the spike's fallback).
  - `POST /api/mail/test`, `POST /api/mail/campaigns`, `POST /api/mail/campaigns/{id}/send`, `POST /api/mail/campaigns/{id}/resume`, `GET /api/mail/campaigns`, `GET /api/mail/campaigns/{id}` behave as spec and plan §Contracts; confirm uses a conditional `UPDATE … WHERE status='draft'`; batches run in `BackgroundTasks` and commit per batch.
  - Quota and the 5-per-hour limit are checked before anything is sent; `MAIL_ENABLED=false` → 503 "El correo está desactivado".
  - Every new write endpoint has a matrix row (OWN with the club audience, or the campaign's sender); `docs/permissions-matrix.md` is regenerated. Tests use a Fake transport through `app.dependency_overrides[get_mail_transport]`.
  - Analytics event `mail.campaign_sent` with the count only.
- **Verify:** `bash .uak/bin/q uv run pytest -q --tb=short -x app/tests/test_mail_template.py app/tests/test_mail_campaigns.py app/tests/test_permissions_matrix.py`
- **Next step:** stubs for the Tests names and `uak red UPS-075`; then the template, then draft and confirm, then background sending.

## UPS-076 · One-click unsubscribe and the "Recibir correos del club" preference

- **Type:** feature
- **Priority:** P1
- **Estimate:** 180 min
- **Rubric / Spec:** `docs/specs/003-correo/spec.md` §Opt-out, `plan.md` §Contracts, §STRIDE (disclosure). RFC 8058. Human owner: victor.
- **Depends on:** UPS-075
- **Uses contract:** None
- **Related:** UPS-079
- **Paths:** app/services/mail_suppressions.py, app/routers/mail_public.py, app/tests/test_mail_unsubscribe.py, app/tests/test_permissions_matrix.py, docs/permissions-matrix.md
- **Freeze-Allowed:** no
- **Tests:** test_one_click_post_form_encoded_suppresses_without_session, test_json_post_from_the_baja_page_suppresses, test_unknown_token_answers_like_a_valid_one, test_token_is_read_from_the_query_not_the_path, test_suppressed_address_is_excluded_from_every_campaign, test_preference_get_and_put_toggle_the_current_address, test_outside_address_can_unsubscribe, test_unsubscribe_is_rate_limited
- **Acceptance:**
  - `POST /api/mail/unsubscribe?t=` accepts `application/x-www-form-urlencoded` (`List-Unsubscribe=One-Click`) and JSON, with no session and no `X-Requested-With`; it looks up the token hash, adds a `mail_suppressions` row (`unsubscribed`) and answers 200 with the same body for unknown tokens.
  - `GET/PUT /api/mail/preferences` for any signed-in user; `receive_club_email=false` adds the suppression of their current address, `true` removes an `unsubscribed` one (never a bounce or complaint).
  - Matrix rows: unsubscribe PUBLIC (the test builds a real token), preferences ANY; docs regenerated. Per-IP rate limit on unsubscribe.
- **Verify:** `bash .uak/bin/q uv run pytest -q --tb=short -x app/tests/test_mail_unsubscribe.py app/tests/test_mail_audience.py app/tests/test_permissions_matrix.py`
- **Next step:** stubs for the Tests names and `uak red UPS-076`; then suppressions, then the public router, then preferences.

## UPS-077 · Mailgun webhook: signed delivery status, bounces and complaints suppress the address

- **Type:** feature
- **Priority:** P2
- **Estimate:** 180 min
- **Rubric / Spec:** `docs/specs/003-correo/spec.md` §History and delivery status, `plan.md` §STRIDE (spoofing), `docs/spikes/mailgun.md` §Webhooks. Human owner: victor.
- **Depends on:** UPS-076, UPS-071
- **Uses contract:** None
- **Related:** UPS-080
- **Paths:** app/services/mail_webhooks.py, app/routers/mail_webhooks.py, app/tests/test_mail_webhooks.py, app/tests/test_permissions_matrix.py, docs/permissions-matrix.md
- **Freeze-Allowed:** no
- **Tests:** test_delivered_event_updates_the_recipient, test_permanent_failure_marks_bounced_and_suppresses, test_temporary_failure_keeps_accepted, test_complaint_suppresses, test_webhook_rejects_bad_signature, test_webhook_rejects_old_timestamp, test_webhook_rejects_replayed_token, test_unknown_campaign_or_recipient_is_ignored_with_200, test_webhook_logs_have_no_addresses
- **Acceptance:**
  - `POST /api/mail/webhooks/mailgun` verifies HMAC-SHA256(`MAILGUN_WEBHOOK_SIGNING_KEY`, timestamp+token) with `hmac.compare_digest`, timestamp within 5 minutes, token seen once (in-memory, one process); otherwise 403 and nothing changes.
  - Events from the UPS-071 fixtures update `mail_recipients` by `(campaign_id, email)`; permanent failures and complaints add a suppression; the campaign's counts change accordingly.
  - Matrix row PUBLIC (the test signs a real payload); docs regenerated.
- **Verify:** `bash .uak/bin/q uv run pytest -q --tb=short -x app/tests/test_mail_webhooks.py app/tests/test_permissions_matrix.py`
- **Next step:** stubs for the Tests names and `uak red UPS-077`; then the signature check, then the event mapping.

## UPS-078 · Web: "Correos" tab in the superadmin panel (composer, audience, preview, test, confirm, history)

- **Type:** feature
- **Priority:** P1
- **Estimate:** 360 min
- **Rubric / Spec:** `docs/specs/003-correo/spec.md` §Stories (superadmin), `plan.md` §Contracts, `web/DESIGN.md` (admin panel recipe). Human owner: victor.
- **Depends on:** UPS-075
- **Uses contract:** None
- **Related:** UPS-079
- **Paths:** web/src/features/mail/, web/src/features/superadmin/index.tsx, e2e/test_mail.py
- **Freeze-Allowed:** no
- **Tests:** test_superadmin_sends_to_a_club_after_preview_and_confirm, test_superadmin_mixes_users_and_outside_addresses, test_test_send_reports_sent_to_me, test_mail_disabled_shows_the_notice, test_history_lists_the_campaign_with_counts, test_mail_tab_at_390_wide
- **Acceptance:**
  - New tab "Correos" in `/admin` (after "Usuarios"): audience picker "Todo UpiixSol" / "Un club" / "Un rol" / "Personas" (search users by name or nickname, plus chips for outside addresses, max 50/20 with live counters), subject, plain-text body with character counter, "Enviarme una prueba".
  - "Revisar y enviar" opens a modal "Se enviará a N personas" (N from the preview endpoint, with excluded counts) and the remaining daily quota; confirm creates the draft and sends it; the button is disabled while sending.
  - History: campaigns with subject, audience, sender, date, status and counts per status; "Interrumpido · Reanudar" when stuck; empty and loading states like the other tabs.
  - `web/src/features/mail/` holds the reusable `Composer`, `AudiencePicker` and `History` (UPS-079 reuses them). Spanish (Mexico), WCAG AA, 1280 and 390 wide, reduced motion; `.uak-shots/UPS-078/` and a `design-critic` SHIP.
  - e2e runs with the console backend (no Mailgun) and checks the history row.
- **Verify:** `bash .uak/bin/q bash -c 'npm --prefix web run lint && npm --prefix web run build && uv run pytest -q e2e/test_mail.py'`
- **Next step:** stubs for the e2e Tests names and `uak red UPS-078`; then `AudiencePicker`, then the confirm modal, then history.

## UPS-079 · Web: "Correos" in the club panel, Mi cuenta toggle and the /baja page

- **Type:** feature
- **Priority:** P1
- **Estimate:** 240 min
- **Rubric / Spec:** `docs/specs/003-correo/spec.md` §Stories (academy admin, member), §Opt-out. Human owner: victor.
- **Depends on:** UPS-078, UPS-076
- **Uses contract:** None
- **Related:** None
- **Paths:** web/src/features/academy-admin/index.tsx, web/src/features/account/index.tsx, web/src/features/account/ProfileTab.tsx, web/src/features/mail/, e2e/test_mail_club.py
- **Freeze-Allowed:** no
- **Tests:** test_club_admin_mails_their_club_only, test_club_admin_picker_lists_only_their_enrollees, test_member_turns_off_club_email_in_mi_cuenta, test_baja_page_confirms_and_unsubscribes, test_baja_page_with_bad_token_shows_the_same_message, test_club_mail_tab_at_390_wide
- **Acceptance:**
  - The club panel gets a "Correos" tab with the same `Composer`, audience limited to "Mi club" and "Personas" (enrollees of the club plus outside addresses), and the club's history.
  - Mi cuenta shows "Recibir correos del club" (switch, saved through `PUT /api/mail/preferences`, with the reason text).
  - New public route `/baja?t=…` (in `web/src/features/mail/index.tsx` `routes`): one button "Darme de baja", then "Listo, ya no recibirás correos del club"; the same message for an unknown token.
  - 1280 and 390 wide, AA, reduced motion; `.uak-shots/UPS-079/` and a `design-critic` SHIP.
- **Verify:** `bash .uak/bin/q bash -c 'npm --prefix web run lint && npm --prefix web run build && uv run pytest -q e2e/test_mail_club.py'`
- **Next step:** stubs for the e2e Tests names and `uak red UPS-079`; then the /baja page, then the toggle, then the club tab.

## UPS-080 · Docs: Mailgun runbook (DNS for mg.upiixsol.com, Render variables, webhook, first send)

- **Type:** docs
- **Priority:** P1
- **Estimate:** 90 min
- **Rubric / Spec:** `docs/specs/003-correo/plan.md` §Rollout and rollback, ADR 0002, `docs/spikes/mailgun.md`. Human owner: victor (every step in the dashboard or DNS is his, never an agent's).
- **Depends on:** UPS-077
- **Uses contract:** None
- **Related:** UPS-071
- **Paths:** docs/mail-mailgun.md, docs/runbook.md, docs/deploy-render.md, render.yaml
- **Freeze-Allowed:** no
- **Test-First:** no (documentation; checked by the Verify grep and by victor following it once)
- **Acceptance:**
  - `docs/mail-mailgun.md` (Spanish): create the domain `mg.upiixsol.com` in Mailgun (region), the DNS records to add (SPF, DKIM, MX, optional tracking CNAME off) and DMARC on `upiixsol.com`, how to check they are verified, the webhook URL `https://www.upiixsol.com/api/mail/webhooks/mailgun` and its events, where the API key and signing key go (Render dashboard only), the rollout steps of plan §Rollout, the rollback (`MAIL_ENABLED=false`) and the monthly retention run (`python -m app.services.mail_retention`, UPS-081).
  - `render.yaml` lists the mail variables (`sync: false` for keys); `docs/runbook.md` and `docs/deploy-render.md` link the new doc.
  - No real key, record value or address beyond the documented `avisos@mg.upiixsol.com` is written in the repo.
- **Verify:** `bash .uak/bin/q bash -c 'test -s docs/mail-mailgun.md && grep -q mg.upiixsol.com docs/mail-mailgun.md && grep -q MAILGUN_API_KEY render.yaml && bash .uak/bin/secret-scan --tracked'`
- **Next step:** write the headings from plan §Rollout, then the DNS table from the spike.

## UPS-081 · Mail retention: delete recipient rows 365 days after the campaign

- **Type:** feature
- **Priority:** P2
- **Estimate:** 90 min
- **Rubric / Spec:** `docs/specs/003-correo/spec.md` §Non-functional (privacy), `plan.md` §Data, §STRIDE (disclosure). Human owner: victor.
- **Depends on:** UPS-077
- **Uses contract:** None
- **Related:** UPS-080
- **Paths:** app/services/mail_retention.py, app/tests/test_mail_retention.py
- **Freeze-Allowed:** no
- **Tests:** test_purge_deletes_recipients_of_old_campaigns_only, test_purge_keeps_campaign_counts, test_purge_keeps_suppressions, test_purge_cli_dry_run_prints_counts_only
- **Acceptance:**
  - `python -m app.services.mail_retention [--days 365] [--dry-run]` deletes `mail_recipients` rows of campaigns finished more than N days ago, after storing their counts per status on the campaign; suppressions are kept; it prints counts only.
  - No scheduler is added; `docs/mail-mailgun.md` (UPS-080) already says to run it monthly.
- **Verify:** `bash .uak/bin/q uv run pytest -q --tb=short -x app/tests/test_mail_retention.py`
- **Next step:** stubs for the Tests names and `uak red UPS-081`; then the query, then the CLI.

## UPS-082 · Web CI: `npm audit` high on picomatch (GHSA-fc5q-39xc-vjpf) without breaking Vite

- **Type:** bug
- **Priority:** P0
- **Estimate:** 90 min
- **Rubric / Spec:** human request (victor) 2026-11-17. The `web` CI job fails on every PR (seen on PR #123, UPS-072) at `npm --prefix web audit --omit=dev --audit-level=high`: picomatch, high, ReDoS through single-branch repeated extglobs (https://github.com/advisories/GHSA-fc5q-39xc-vjpf), reached through `@tailwindcss/vite` → `vite` → `fdir` → `picomatch`. npm's suggestion (`npm audit fix --force`, which installs `vite@6.2.7`) is a breaking downgrade and is NOT an acceptable fix. `.uak/docs/SECURITY.md` §dependencies applies.
- **Depends on:** None
- **Uses contract:** None
- **Related:** UPS-001, UPS-072
- **Paths:** web/package.json, web/package-lock.json, docs/security-deps.md
- **Freeze-Allowed:** yes
- **Test-First:** no (dependency fix: the red check is the failing audit itself; reproduce it first)
- **Acceptance:**
  - First reproduce the failure locally (`npm --prefix web ci && npm --prefix web audit --omit=dev --audit-level=high` exits non-zero) and record the advisory's affected and patched versions from the advisory page.
  - Fix in this order of preference, stopping at the first that works: (a) build-only packages (`@tailwindcss/vite`, `tailwindcss`) move to `devDependencies`, since nothing at runtime imports them, so the production tree no longer contains vite/picomatch; (b) an `overrides` entry pins `picomatch` to the patched version; (c) if no patched version exists, stop and ask the human with `uak decision UPS-082 --class scope` (never disable or weaken the audit step, never `--force`).
  - Vite stays on its current major (`^8`); `npm --prefix web run lint`, `npm --prefix web run build` and the Docker build stage that runs `npm ci` keep working (check the Dockerfile still installs devDependencies for the build).
  - `docs/security-deps.md` (Spanish, short) records the advisory, the path, the fix chosen and why, and the date.
  - CI `web` is green on the PR.
- **Verify:** `bash .uak/bin/q bash -c 'npm --prefix web ci && npm --prefix web audit --omit=dev --audit-level=high && npm --prefix web run lint && npm --prefix web run build'`
- **Next step:** reproduce the audit failure, then try (a).

## UPS-083 · Tests ignore the developer's `.env`: the backend suite is hermetic

- **Type:** bug
- **Priority:** P1
- **Estimate:** 120 min
- **Rubric / Spec:** human request (victor) 2026-11-17. `Settings` reads `.env` (`app/config.py`, `env_file=".env"`), and `wt new` links the main checkout's `.env` into every worktree, so a developer's `.env` copied from `.env.example` makes 23 backend tests fail in upload, site, auth and analytics code, while the same commit passes all 741 tests and smoke without it (found by victor-2 on UPS-074, recorded with `uak learn`). CI has no `.env`, so CI stays green and hides it. Tests must never depend on a developer's local configuration.
- **Depends on:** None
- **Uses contract:** None
- **Related:** UPS-074, UPS-020
- **Paths:** app/tests/conftest.py, app/config.py, app/tests/test_settings_isolation.py
- **Freeze-Allowed:** yes
- **Tests:** test_settings_ignore_dotenv_under_pytest, test_suite_settings_match_defaults_with_a_full_dotenv_present
- **Acceptance:**
  - First find which variables cause the 23 failures (run the suite with a `.env` that has every `.env.example` key, then bisect); record them in the PR description. Never read, print or commit the real `.env`: build a throwaway one from `.env.example` in a temp dir.
  - Under pytest, `Settings` does not read any `.env` file (e.g. the test settings are built with `_env_file=None`, or `conftest.py` sets that before the app is imported); explicit environment variables and `monkeypatch` still work as today.
  - The full backend suite passes in a worktree that has the main checkout's `.env` linked, and in a clean checkout without it; the app outside tests still reads `.env` as before (dev and prod unchanged).
  - No existing test is edited to pass.
- **Verify:** `bash .uak/bin/q uv run pytest -q --tb=short -x`
- **Next step:** reproduce with a throwaway `.env` built from `.env.example`, find the variables, then the stub test and `uak red UPS-083`.

## UPS-084 · Migrations refuse `downgrade` against a remote database (incident 2026-11-17)

- **Type:** bug
- **Priority:** P0
- **Estimate:** 120 min
- **Rubric / Spec:** incident 2026-11-17, human request (victor). An agent ran the UPS-072 Verify (`uv run alembic upgrade head && uv run alembic downgrade base`) in a worktree whose linked dotenv file pointed `DATABASE_URL` at the production Neon database: the log (`.git/worktrees/ups-072/uak-out/q-1794938524-15246.log`) shows `Context impl PostgresqlImpl` and `downgrade 0009 → … → base`, which dropped every table. Neon point-in-time restore recovered it. `app/migrations/env.py` takes the URL from `get_settings().database_url` with no guard, and `wt new` links the main checkout's dotenv file into every worktree, so any `alembic downgrade` in any worktree reaches whatever that file points to.
- **Depends on:** None
- **Uses contract:** None
- **Related:** UPS-083, UPS-072, UPS-070
- **Paths:** app/migrations/env.py, app/tests/test_migration_guard.py, .claude/CLAUDE.md, docs/runbook.md
- **Freeze-Allowed:** yes
- **Tests:** test_downgrade_refused_on_remote_postgres, test_downgrade_allowed_on_sqlite_and_localhost, test_downgrade_allowed_on_remote_with_explicit_override, test_upgrade_still_runs_on_remote
- **Acceptance:**
  - `app/migrations/env.py` refuses any downgrade (exit non-zero, clear Spanish message, nothing executed) when the URL is not SQLite and its host is not `localhost`/`127.0.0.1`/`::1`, unless `ALEMBIC_ALLOW_REMOTE_DOWNGRADE=yes` is set for that one command. Upgrades are unchanged (the Render entrypoint keeps running `alembic upgrade head`).
  - CI keeps passing: its round-trip runs against SQLite and the PostgreSQL 16 service on localhost.
  - Tests never touch a real remote database: they check the guard with fake URLs (no connection is opened before the check).
  - `.claude/CLAUDE.md` "Migrations must round-trip" line shows the safe form `DATABASE_URL=sqlite:////tmp/rt.db uv run alembic upgrade head && DATABASE_URL=sqlite:////tmp/rt.db uv run alembic downgrade base`. Edit it only when no agent session is running (prompt cache), or record it with `uak decision` first.
  - `docs/runbook.md` gets a short "Nunca apuntes el .env local a producción" note and how to restore from Neon history (what was done on 2026-11-17).
  - A `uak learn` line on `app/migrations/` so the next agent sees the rule.
- **Verify:** `bash .uak/bin/q bash -c 'uv run pytest -q --tb=short -x app/tests/test_migration_guard.py && DATABASE_URL=sqlite:////tmp/ups084.db uv run alembic upgrade head && DATABASE_URL=sqlite:////tmp/ups084.db uv run alembic downgrade base'`
- **Next step:** stubs for the Tests names and `uak red UPS-084`; then the guard in env.py.

## UPS-085 · Contract: email blocks schema, migration 0010, attachments and Reply-To in the transport

- **Type:** contract
- **Priority:** P1
- **Estimate:** 180 min
- **Rubric / Spec:** `docs/specs/004-correo-bonito/spec.md` §Content and rendering, `plan.md` §Data and migrations, §Contracts. Human owner: victor.
- **Depends on:** UPS-081
- **Uses contract:** None
- **Related:** UPS-086, UPS-087, UPS-088, UPS-089
- **Paths:** app/services/mail_blocks.py, app/models/mail.py, app/migrations/versions/0010_mail_blocks.py, app/services/mailer.py, app/services/mailgun.py, app/tests/test_mail_blocks.py, app/tests/test_mailgun.py, web/src/lib/types.ts
- **Freeze-Allowed:** no
- **Tests:** test_blocks_accept_each_kind, test_blocks_reject_unknown_kind_and_extra_fields, test_blocks_limit_30_and_one_event, test_event_block_needs_event_id_or_title_start_end, test_event_end_after_start, test_typed_event_naive_time_is_mexico_city, test_button_and_image_urls_must_be_http, test_reply_to_with_newline_is_422, test_mail_blocks_migration_round_trips_on_sqlite, test_mailgun_sends_attachment_and_reply_to, test_mailgun_from_name_keeps_the_address, test_from_name_is_sanitized
- **Acceptance:**
  - `app/services/mail_blocks.py`: Pydantic discriminated union `Block` (`heading`, `paragraph`, `list`, `button`, `event`, `image`, `divider`) with the limits of spec 004, `Blocks` (1–30, ≤ 1 event), `ReplyTo` (one address, no CR/LF), Spanish 422 messages; `extra="forbid"`. Typed event start/end without an offset are America/Mexico_City (UTC-6), with an offset they are converted; stored in UTC (a typed 15:00 is `21:00Z`).
  - Migration `0010_mail_blocks` (down_revision `0009`) adds `content` JSON, `sender_academy_id` (FK academies, SET NULL; NULL = UpiixSol), `preheader`, `reply_to`, `ics_token` (unique) to `mail_campaigns`; additive only. Its round-trip test and Verify use a temp SQLite only (never the dotenv `DATABASE_URL`).
  - `MailMessage` gains `attachments`, `reply_to` and `from_name`; `MailgunTransport` sends `attachment` parts, `h:Reply-To` (campaign value over `MAIL_REPLY_TO`) and `from` as `"<from_name> · UpiixSol" <address of MAIL_FROM>` when `from_name` is set (name sanitized: one line, no quotes or `<>`). Existing tests keep passing unchanged.
  - `web/src/lib/types.ts` mirrors `Block`, `Blocks`, `PreviewOut`; also fix `AudienceOut.email_count` → `outside` (UPS-078 note).
- **Verify:** `bash .uak/bin/q bash -c 'uv run pytest -q --tb=short -x app/tests/test_mail_blocks.py app/tests/test_mailgun.py app/tests/test_mail_contract.py && DATABASE_URL=sqlite:////tmp/ups085.db uv run alembic upgrade head && DATABASE_URL=sqlite:////tmp/ups085.db uv run alembic downgrade base && npm --prefix web run build'`
- **Next step:** stubs for the Tests names and `uak red UPS-085`; then the block models, then the migration, then the transport.

## UPS-086 · Email renderer: designed layout, club theme, blocks to HTML and text, preheader, footer with Reply-To

- **Type:** feature
- **Priority:** P1
- **Estimate:** 300 min
- **Rubric / Spec:** `docs/specs/004-correo-bonito/spec.md` §Content and rendering, §Compatibility, §Non-functional, `plan.md` §Design, §STRIDE (tampering). Human owner: victor. Skill: frontend-design for the visual direction (brand palettes in IDEA §0.1, logos used as-is).
- **Depends on:** UPS-085
- **Uses contract:** None
- **Related:** UPS-087, UPS-089
- **Paths:** app/services/mail_render.py, app/tests/test_mail_render.py, app/tests/fixtures/mail_render/
- **Freeze-Allowed:** no
- **Tests:** test_layout_is_600px_tables_with_inline_styles, test_upiixsol_logo_always_on_top, test_sender_block_shows_club_logo_name_and_color, test_sender_block_for_the_board, test_theme_uses_sender_club_colors, test_theme_falls_back_to_site_brand, test_svg_club_logo_falls_back, test_preheader_is_hidden_text, test_paragraph_html_is_escaped, test_bold_italic_and_links_are_rendered, test_javascript_link_is_dropped, test_button_is_bulletproof_cell, test_image_has_alt_and_absolute_url, test_event_card_shows_mexico_city_time, test_footer_with_and_without_reply_to, test_text_part_matches_blocks, test_html_size_cap
- **Acceptance:**
  - `render_blocks(campaign_like, *, sender, theme, recipient_name, unsubscribe_href, event, ics_url) -> (html, text)`: table layout ≤ 600 px, inline styles only, the UpiixSol logo always on top, then the sender block "Enviado por <club>" (club logo or name as wordmark, accent color) or "Enviado por la mesa directiva de UpiixSol", accent colors from the sender club, hidden preheader, a design that survives the forced color inversion of Gmail dark mode (iOS/Android ignore `color-scheme`): transparent logo, no text baked into images, contrast checked in both light and inverted colors, bulletproof buttons (background on the cell), images with alt and absolute URLs, an event card (weekday, date and time in America/Mexico_City, place, description, link, and the three calendar links passed in), divider, footer with why you got it, Reply-To line and "Darte de baja".
  - Inline formatting: escape first, then `**b**`, `*i*`, `[t](url)` with `safe_url`; never raw HTML. The plain-text part carries the same content.
  - The HTML of a 30-block email stays ≤ 100 KB. A few rendered fixtures (`app/tests/fixtures/mail_render/*.html`) are kept as golden files for review and the design critic.
  - Legacy campaigns keep using `mail_template.render` (unchanged).
- **Verify:** `bash .uak/bin/q uv run pytest -q --tb=short -x app/tests/test_mail_render.py app/tests/test_mail_template.py`
- **Next step:** stubs for the Tests names and `uak red UPS-086`; then the layout skeleton, then each block, then the footer.

## UPS-087 · Calendar: event card links, `.ics` attachment and public `.ics` URL, events picked from the campus

- **Type:** feature
- **Priority:** P1
- **Estimate:** 240 min
- **Rubric / Spec:** `docs/specs/004-correo-bonito/spec.md` §Events and calendar, `plan.md` §Design (calendar), §STRIDE. RFC 5545. Human owner: victor.
- **Depends on:** UPS-085
- **Uses contract:** None
- **Related:** UPS-086, UPS-089, UPS-091
- **Paths:** app/services/mail_ics.py, app/routers/mail_ics.py, app/tests/test_mail_ics.py
- **Freeze-Allowed:** no
- **Tests:** test_ics_is_rfc5545_with_crlf_folding_and_escaping, test_ics_uses_utc_and_stable_uid, test_typed_15h_is_210000Z_in_ics_and_google, test_google_calendar_url, test_outlook_calendar_url, test_resolve_event_block_from_campus_event, test_academy_admin_cannot_reference_other_club_event, test_ics_endpoint_serves_text_calendar, test_unknown_ics_token_is_404
- **Acceptance:**
  - `mail_ics.py`: `build_ics(event, uid) -> bytes` (`METHOD:PUBLISH`, `VEVENT` with `UID`, `DTSTAMP`, `DTSTART`/`DTEND` in UTC, `SUMMARY`, `LOCATION`, `DESCRIPTION`, `URL`), `google_url(event)`, `outlook_url(event)`, `resolve_event(db, sender, block)` (campus event by id with club scope from the DB row, or the typed fields).
  - `GET /api/mail/ics/{token}.ics`: public, `text/calendar; charset=utf-8`, `Content-Disposition: attachment; filename="evento.ics"`; 404 for unknown tokens; read-matrix row PUBLIC (in `test_mail_ics.py` if the matrix file is busy; otherwise the matrix).
  - No dependency added.
- **Verify:** `bash .uak/bin/q uv run pytest -q --tb=short -x app/tests/test_mail_ics.py`
- **Next step:** stubs for the Tests names and `uak red UPS-087`; then the ICS writer, then the URLs, then the endpoint.

## UPS-088 · Email images: PNG/JPEG copies under /media/mail, upload endpoint, logos and covers usable in email

- **Type:** feature
- **Priority:** P1
- **Estimate:** 210 min
- **Rubric / Spec:** `docs/specs/004-correo-bonito/spec.md` §Images, `plan.md` §STRIDE (DoS). WebP is not shown by Outlook desktop and no email client shows SVG. Human owner: victor.
- **Depends on:** UPS-085
- **Uses contract:** None
- **Related:** UPS-086, UPS-091
- **Paths:** app/services/media.py, app/services/mail_images.py, app/routers/mail_images.py, app/tests/test_mail_images.py, app/tests/test_permissions_matrix.py, docs/permissions-matrix.md
- **Freeze-Allowed:** no
- **Tests:** test_upload_png_jpg_webp_stores_jpeg_or_png_copy, test_svg_is_refused, test_email_image_too_large_is_413, test_resized_to_1200_wide, test_mail_media_is_public_without_session, test_email_copy_of_site_logo_and_event_cover, test_svg_club_logo_falls_back_to_site_logo_or_wordmark, test_member_and_anon_cannot_upload
- **Acceptance:**
  - `media.py`: a `mail` kind that writes `mail/<uuid>.jpg|png` (MEDIA_KEY and CONTENT_TYPES accept them) in both storage modes; existing kinds unchanged.
  - `POST /api/mail/images` (superadmin, academy_admin; per-user rate limit) → `{url}` absolute under `PUBLIC_BASE_URL`; real-type check, ≤ 5 MB, re-encode ≤ 1200 px wide (photos JPEG, transparency PNG).
  - `email_copy(url) -> url | None`: cached PNG/JPEG copy of a WebP site/club logo or event cover, for the renderer. An SVG logo cannot be rasterized without a new dependency: it returns None and the renderer falls back to the site logo, else the text wordmark.
  - Write-matrix row (OWN-like: superadmin and academy_admin; member 403, anon 401).
- **Verify:** `bash .uak/bin/q uv run pytest -q --tb=short -x app/tests/test_mail_images.py app/tests/test_media.py app/tests/test_media_storage.py app/tests/test_permissions_matrix.py`
- **Next step:** stubs for the Tests names and `uak red UPS-088`; then the media kind, then the endpoint, then `email_copy`.

## UPS-089 · Campaign API: blocks, preview, Reply-To, `.ics` attached at send, test send removed

- **Type:** feature
- **Priority:** P1
- **Estimate:** 300 min
- **Rubric / Spec:** `docs/specs/004-correo-bonito/spec.md` §Preview, test send and Reply-To, §Compatibility, `plan.md` §Contracts. Human owner: victor.
- **Depends on:** UPS-086, UPS-087, UPS-088, UPS-092
- **Uses contract:** None
- **Related:** UPS-090, UPS-091
- **Paths:** app/services/mail_campaigns.py, app/routers/mail_campaigns.py, app/tests/test_mail_campaigns.py, app/tests/test_mail_preview.py, app/tests/test_permissions_matrix.py, docs/permissions-matrix.md, docs/mail-mailgun.md
- **Freeze-Allowed:** no
- **Tests:** test_create_campaign_with_blocks_preheader_and_reply_to, test_superadmin_picks_sender_club_or_board, test_academy_admin_sender_is_always_own_club, test_send_uses_sender_in_from_name_and_header, test_preview_returns_the_same_html_as_send, test_preview_scoped_like_create, test_send_attaches_evento_ics_and_sets_reply_to, test_event_resolved_at_send_time, test_legacy_body_campaign_still_sends_and_lists, test_test_send_endpoint_is_gone
- **Acceptance:**
  - `POST /api/mail/campaigns` takes `sender_academy_id?`, `preheader?`, `reply_to?`, `blocks` (legacy `body` still accepted); an academy_admin's sender is forced to their club (from the DB); a superadmin's defaults to the audience's club, else UpiixSol (NULL), and must be an active club; stores `content`, generates `ics_token` when there is an event block.
  - History shows the sender (UpiixSol or the club).
  - `POST /api/mail/preview` returns `{html, text}` from `mail_render` with a sample recipient name and a dummy unsubscribe link; same scope checks as create.
  - Sending renders blocks with the audience theme, attaches `evento.ics`, sets Reply-To (campaign over setting); history lists both kinds.
  - `POST /api/mail/test` and its matrix row and tests are removed. Removing existing tests needs a human first: `UAK_HUMAN=victor bash .uak/bin/uak allow UPS-089 --tests --reason 'victor removed the test send (spec 004)'`.
  - `docs/mail-mailgun.md`: `MAIL_REPLY_TO` (default inbox, set in Render), how images and `.ics` work, a real-send checklist (Gmail web, Gmail iOS dark mode, Apple Mail, Outlook) and a note that on Render free images may fail to load during a cold start.
- **Verify:** `bash .uak/bin/q uv run pytest -q --tb=short -x app/tests/test_mail_campaigns.py app/tests/test_mail_preview.py app/tests/test_permissions_matrix.py`
- **Next step:** after the human `uak allow`, stubs for the Tests names and `uak red UPS-089`; then create + preview, then send, then the removal.

## UPS-090 · Web: block composer with live preview (desktop / phone), test send removed

- **Type:** feature
- **Priority:** P1
- **Estimate:** 360 min
- **Rubric / Spec:** `docs/specs/004-correo-bonito/spec.md` §Stories, §Preview, `plan.md` §STRIDE (sandboxed iframe), `web/DESIGN.md`. Human owner: victor. Skills: product-ui, stack-frontend.
- **Depends on:** UPS-089
- **Uses contract:** None
- **Related:** UPS-091
- **Paths:** web/src/features/mail/Composer.tsx, web/src/features/mail/BlockEditor.tsx, web/src/features/mail/EmailPreview.tsx, web/src/features/mail/blocks.ts, e2e/test_mail.py, e2e/test_mail_club.py
- **Freeze-Allowed:** no
- **Tests:** test_composer_builds_title_paragraph_button_and_previews, test_preview_iframe_is_sandboxed, test_preview_switches_desktop_and_phone, test_blocks_reorder_and_delete, test_button_presets_campus_and_club, test_sender_selector_for_superadmin_and_fixed_for_club_admin, test_no_test_send_button, test_composer_at_390_wide
- **Acceptance:**
  - Subject, preheader and a block list: add (Título, Párrafo, Lista, Botón, Evento, Imagen, Separador), edit inline, move up/down, delete; a short formatting hint for `**negritas**`, `*cursivas*`, `[texto](url)`.
  - Live preview beside the editor on desktop and below on phones: `iframe srcdoc` with `sandbox=""`, toggles 600 / 375 px, refreshed 400 ms after the last change through `POST /api/mail/preview`.
  - "Enviado por": a selector (UpiixSol or a club) for the superadmin, defaulting to the audience's club; fixed and shown (not editable) for a club admin; the preview shows the sender block.
  - Button presets "Ir al campus" and "Ver el club". "Enviarme una prueba" is gone. "Revisar y enviar" keeps the count modal.
  - Same composer in the superadmin tab and the club panel. Spanish (Mexico), AA, reduced motion; `.uak-shots/UPS-090/` and a design-critic SHIP.
  - UPS-078/079 e2e tests that use the test send or type into the plain body field change (e.g. `test_test_send_reports_sent_to_me` is removed). A human runs first: `UAK_HUMAN=victor bash .uak/bin/uak allow UPS-090 --tests --reason 'victor: block composer replaces the plain body and the test send (spec 004)'`.
- **Verify:** `bash .uak/bin/q bash -c 'npm --prefix web run lint && npm --prefix web run build && uv run pytest -q e2e/test_mail.py e2e/test_mail_club.py'`
- **Next step:** after the human `uak allow`, stubs for the e2e Tests names and `uak red UPS-090`; then the block list, then the preview, then the presets.

## UPS-091 · Web: event block (from the calendar or by hand), image block with upload, Reply-To field

- **Type:** feature
- **Priority:** P1
- **Estimate:** 300 min
- **Rubric / Spec:** `docs/specs/004-correo-bonito/spec.md` §Events and calendar, §Images, §Preview, test send and Reply-To. Human owner: victor. Skills: product-ui, stack-frontend.
- **Depends on:** UPS-090
- **Uses contract:** None
- **Related:** None
- **Paths:** web/src/features/mail/EventBlockEditor.tsx, web/src/features/mail/ImageBlockEditor.tsx, web/src/features/mail/ReplyToField.tsx, web/src/features/mail/BlockEditor.tsx, e2e/test_mail_rich.py
- **Freeze-Allowed:** no
- **Tests:** test_event_block_from_campus_calendar_shows_card_and_calendar_links, test_event_block_typed_by_hand, test_image_block_uploads_and_previews, test_reply_to_prefilled_and_editable, test_club_admin_sees_only_global_and_own_club_events
- **Acceptance:**
  - Event block: "Del calendario" (search the campus events through `GET /api/events`, the club admin sees global and own-club events) or "Escribir evento" (title, start, end, place, description, link); the preview shows the card with Google Calendar, Outlook and Apple/.ics.
  - Image block: upload (png/jpg/webp ≤ 5 MB) with progress and errors in Spanish, alt text required, optional link; also "Usar la portada del evento".
  - Reply-To field prefilled from settings (shown, editable, validated).
  - The e2e fixture sets `PUBLIC_BASE_URL` to the e2e server so uploaded images load in the preview; check that the app CSP `img-src` allows them inside the `srcdoc` iframe.
  - 1280 and 390 wide, AA, reduced motion; `.uak-shots/UPS-091/` and a design-critic SHIP.
- **Verify:** `bash .uak/bin/q bash -c 'npm --prefix web run lint && npm --prefix web run build && uv run pytest -q e2e/test_mail_rich.py'`
- **Next step:** stubs for the e2e Tests names and `uak red UPS-091`; then the event picker, then the image upload, then Reply-To.

## UPS-092 · Mail quota per Mailgun billing period (3,000 a month) instead of 100 a day

- **Type:** feature
- **Priority:** P1
- **Estimate:** 150 min
- **Rubric / Spec:** human request (victor) 2026-11-17. The daily cap `MAIL_DAILY_LIMIT=100` was a placeholder from plan 003, never verified. victor's Mailgun plan is **Free: 3,000 emails per month, counted per billing period** (screenshot in the chat: "Emails sent this billing period 2 / 3,000"). Replace the daily cap with a monthly one that follows the billing period. Spec 003 §Composing and sending (quota) changes from "today" to "this billing period".
- **Depends on:** UPS-085
- **Uses contract:** None
- **Related:** UPS-089, UPS-090
- **Paths:** app/config.py, .env.example, render.yaml, app/services/mail_audience.py, app/services/mail_campaigns.py, web/src/lib/types.ts, web/src/features/mail/Composer.tsx, docs/mail-mailgun.md, docs/specs/003-correo/spec.md, app/tests/test_mail_quota.py, app/tests/test_mail_audience.py, app/tests/test_mail_campaigns.py, app/tests/test_mail_contract.py, app/tests/test_settings_isolation.py
- **Freeze-Allowed:** no
- **Tests:** test_quota_counts_the_current_billing_period, test_period_starts_on_configured_day, test_period_rolls_over_at_month_end_for_short_months, test_monthly_quota_exceeded_is_422_before_sending, test_status_reports_monthly_limit_used_remaining_and_renewal_date, test_monthly_settings_defaults_and_validation
- **Acceptance:**
  - Settings: `MAIL_MONTHLY_LIMIT` (default 3000, ≥ 0) and `MAIL_PERIOD_START_DAY` (1–28, default 1: the day of the month the Mailgun billing period starts, UTC). `MAIL_DAILY_LIMIT` is removed (an old value in the environment is ignored).
  - The quota is a DB count of recipients sent (status ≠ `pending`) since the start of the current period; a send that would exceed `remaining` is refused with 422 before calling Mailgun, with the remaining number and the renewal date in Spanish.
  - `GET /api/mail/status` returns `{enabled, monthly_limit, sent_this_period, remaining, period_start, period_end}`; the composer says "Te quedan N de 3,000 correos este mes · se renueva el D de mes".
  - Note in `docs/mail-mailgun.md`: Mailgun also counts sends made outside the app (curl tests, other tools), so leave a margin; set `MAIL_PERIOD_START_DAY` to the day shown in Mailgun → Billing.
  - Existing tests that assert the daily cap change (`test_mail_audience.py` status, `test_mail_campaigns.py` quota, `test_mail_contract.py` and `test_settings_isolation.py` setting names). A human runs first: `UAK_HUMAN=victor bash .uak/bin/uak allow UPS-092 --tests --reason 'victor: monthly Mailgun quota replaces the daily placeholder'`.
- **Verify:** `bash .uak/bin/q bash -c 'uv run pytest -q --tb=short -x app/tests/test_mail_quota.py app/tests/test_mail_audience.py app/tests/test_mail_campaigns.py app/tests/test_mail_contract.py app/tests/test_settings_isolation.py && npm --prefix web run build'`
- **Next step:** after the human `uak allow`, stubs for the Tests names and `uak red UPS-092`; then the period math, then status and the send check, then the composer text.

## UPS-093 · The superadmin turns members into club admins and back

- **Type:** feature
- **Priority:** P0
- **Estimate:** 150 min
- **Rubric / Spec:** human request (cris) 2026-11-17 · `docs/specs/005-eventos-foto-y-roles/spec.md`. Reverses, for the club-admin role only, the 2026-11-12 decision that dropped UPS-066 and left ROL-07 unimplemented.
- **Depends on:** None
- **Uses contract:** None
- **Related:** UPS-094
- **Paths:** app/routers/admin.py, app/services/admin.py, app/schemas/users.py, app/tests/test_admin_roles.py, app/tests/test_permissions_matrix.py, docs/permissions-matrix.md, docs/specs/001-campus/spec.md, web/src/features/superadmin/index.tsx, e2e/test_admin_roles.py, CHANGELOG.md
- **Freeze-Allowed:** no
- **Tests:** superadmin_makes_a_member_a_club_admin_of_an_active_club, superadmin_makes_a_club_admin_a_member_and_clears_the_club, rejects_superadmin_role_and_missing_or_inactive_club_with_422, refuses_own_role_and_superadmin_targets_with_409, new_role_applies_on_next_request_and_logs_without_pii
- **Acceptance:**
  - `PUT /api/admin/users/{user_id}/role` with `{"role": "academy_admin", "academy_id": N}` sets the role and club of an active member and returns `UserAdminOut`; with `{"role": "member"}` it sets `member` and clears `academy_id`, keeping the user's enrollments. `PATCH /api/admin/users/{id}` still rejects `role` (the mass-assignment guard and its tests are untouched).
  - `superadmin` as the new role is 422; a missing, unknown or inactive club for `academy_admin` is 422; an unknown user is 404; an inactive user is 409; changing your own role is 409 ("No puedes cambiar tu propio rol."); a target that is already `superadmin` is 409.
  - The role is read from the DB on every request, so the user gets (or loses) the club panel on their next request; a demoted admin gets 403 on club-admin endpoints at once. One structured log line `role.changed` with actor id, target id, old and new role, with no email or name.
  - The matrix gets a row for `PUT /api/admin/users/{user_id}/role`: only the superadmin is allowed (member, both admins and anonymous denied); `docs/permissions-matrix.md` is regenerated with `uv run python -m app.tests.test_permissions_matrix`; `docs/specs/001-campus/spec.md` ROL-07 note updated.
  - Recipe: list · Hero: the role badge and the "Hacer admin de un club" action in each row of the Usuarios tab. A club picker and a confirmation dialog that names the person and the club ("¿Hacer admin de UpiixIA a Ana Pérez?"); "Quitar admin" asks too; success and error messages in Spanish; keyboard-operable; screenshots at 1280 and 390 in `.uak-shots/UPS-093/` and a `design-critic` SHIP.
  - E2E in a real browser: the superadmin promotes the demo member, who then reaches the club panel, and demotes them again.
  - `CHANGELOG.md` entry; `bash .uak/bin/smoke` exits 0.
- **Verify:** `bash .uak/bin/q bash -c 'uv run ruff check app && uv run pytest -q --tb=short -x app/tests/test_admin_roles.py app/tests/test_admin.py app/tests/test_permissions_matrix.py && npm --prefix web run lint && npm --prefix web run build'`
- **Next step:** stubs for the `Tests:` names and `uak red UPS-093`; then `change_role` in `app/services/admin.py`, the route and schema, the matrix row, then the Usuarios tab.

## UPS-094 · Photo on events: upload, replace, remove and show

- **Type:** feature
- **Priority:** P0
- **Estimate:** 150 min
- **Rubric / Spec:** human request (cris) 2026-11-17 · `docs/specs/005-eventos-foto-y-roles/spec.md`
- **Depends on:** UPS-093 (only because both add rows to `app/tests/test_permissions_matrix.py` and `docs/permissions-matrix.md`)
- **Uses contract:** None
- **Related:** UPS-093, UPS-087
- **Paths:** app/routers/events.py, app/services/events.py, app/schemas/content.py, app/tests/test_events.py, app/tests/test_event_cover.py, app/tests/test_permissions_matrix.py, docs/permissions-matrix.md, web/src/features/events/index.tsx, web/src/features/home/index.tsx, web/src/features/academy/index.tsx, web/src/lib/types.ts, e2e/test_events_cover.py, CHANGELOG.md
- **Freeze-Allowed:** no
- **Tests:** manager_uploads_replaces_and_removes_an_event_cover, academy_admin_cannot_touch_the_cover_of_another_club_or_a_global_event, rejects_svg_fake_image_and_oversized_cover, deleting_an_event_deletes_its_cover_after_commit, event_payload_carries_cover_url_and_no_personal_data
- **Acceptance:**
  - `POST /api/events/{event_id}/cover` (multipart `file`) stores the image as kind `cover` (real type from the bytes, ≤ 5 MB, ≤ 1600 px, re-encoded, no SVG), sets `events.cover_url` and returns the event; `DELETE /api/events/{event_id}/cover` clears it. The old file is deleted only after the commit (same flow as the blog cover upload); deleting an event deletes its cover the same way.
  - `superadmin` can do it on any event; `academy_admin` only on events of their own club, with the scope read from the event row; another club's event or a global event is 403; member 403; anonymous 401. A bad file leaves the event unchanged (422 or 413 with the existing media error).
  - The permission matrix gets rows for both routes; `docs/permissions-matrix.md` is regenerated.
  - Recipe: flow · Hero: the "Foto del evento" field with its preview in the event form (create and edit). PNG, JPG or WebP; the form sends the event first and then the photo; if the photo fails it says "El evento se publicó, pero la foto no se pudo subir. Intenta de nuevo." and keeps the event. The calendar list, the club page and the home show the photo when `cover_url` starts with `/media/`, with `alt=""` and no layout shift (fixed aspect ratio), and the current layout when there is none. Screenshots at 1280 and 390 in `.uak-shots/UPS-094/` and a `design-critic` SHIP.
  - E2E in a real browser: publish an event with a photo, see it in the calendar, replace it, remove it.
  - `CHANGELOG.md` entry; `bash .uak/bin/smoke` exits 0.
- **Verify:** `bash .uak/bin/q bash -c 'uv run ruff check app && uv run pytest -q --tb=short -x app/tests/test_event_cover.py app/tests/test_events.py app/tests/test_permissions_matrix.py && npm --prefix web run lint && npm --prefix web run build'`
- **Next step:** stubs for the `Tests:` names and `uak red UPS-094`; then `replace_cover` and `remove_cover` in `app/services/events.py` copying the blog cover flow, the two routes, the matrix rows, then the form field and the cards.

## UPS-095 · Logos and mascots with a transparent background

- **Type:** feature
- **Priority:** P1
- **Estimate:** 180 min
- **Rubric / Spec:** human request (cris) 2026-11-17 · `docs/specs/006-logos-transparentes/spec.md`
- **Depends on:** None
- **Uses contract:** None
- **Related:** UPS-093, UPS-094
- **Paths:** app/services/media.py, app/services/academy_admin.py, app/services/site.py, app/routers/academy_admin.py, app/routers/site.py, app/tests/test_logo_transparency.py, web/src/features/academy-admin/index.tsx, web/src/features/superadmin/SiteBrandTab.tsx, e2e/test_logo_transparent.py, CHANGELOG.md
- **Freeze-Allowed:** no
- **Tests:** removes_only_the_white_connected_to_the_border_and_keeps_enclosed_white, jpg_and_opaque_png_become_rgba_and_real_transparency_is_kept_as_is, stores_unchanged_when_there_is_no_white_border, refuses_a_mostly_white_image_with_422, svg_is_never_processed_and_the_flag_defaults_to_false
- **Acceptance:**
  - `remove_white_background` in `app/services/media.py` makes transparent only near-white pixels (each channel ≥ 245) connected to the image border, with a soft edge and no white halo; white enclosed by the artwork stays opaque. JPG and no-alpha images are converted to `RGBA` first; images that already have real transparency are stored as is; SVG is never touched.
  - No near-white border: stored unchanged and the response says "No encontramos un fondo blanco para quitar."; more than 98 % transparent: 422 and the logo is unchanged.
  - The four existing routes (`POST /api/academies/{academy_id}/logo|mascot` and `POST /api/admin/site/logo|mascot`) take an optional multipart field `transparent_background` (default `false`, only for `logo` and `mascot`); permissions, responses and the permission matrix do not change, and no new route exists. A 1024 px logo is processed in under a second.
  - Recipe: flow · Hero: the logo and mascot upload cards of the club panel and the brand tab, with a "Quitar el fondo blanco" checkbox (checked by default), a preview on a light and a dark checkerboard swatch, and a "Quitar fondo blanco al logo actual" button that re-sends the current same-origin `/media/…` image through the same route (only paths accepted by `safeAssetPath`). Spanish copy, keyboard-operable, screenshots at 1280 and 390 in `.uak-shots/UPS-095/` and a `design-critic` SHIP.
  - E2E in a real browser: upload a logo on a white background with the box checked and see it over the dark theme without a white box; upload a mostly white image and see the error.
  - `assets/brand/` and the built-in wordmark are never processed. `CHANGELOG.md` entry; `bash .uak/bin/smoke` exits 0.
- **Verify:** `bash .uak/bin/q bash -c 'uv run ruff check app && uv run pytest -q --tb=short -x app/tests/test_logo_transparency.py app/tests/test_media.py app/tests/test_media_storage.py app/tests/test_academy_admin.py app/tests/test_permissions_matrix.py && npm --prefix web run lint && npm --prefix web run build'`
- **Next step:** stubs for the `Tests:` names and `uak red UPS-095`; then `remove_white_background` with `ImageDraw.floodfill` on a border-padded mask, the flag in `save_image_bytes`, the form field in the two routers, then the checkbox, preview and button.

## UPS-096 · Turn on Mailgun batch sending: the per-recipient unsubscribe header is verified

- **Type:** feature
- **Priority:** P1
- **Estimate:** 60 min
- **Rubric / Spec:** human-verified 2026-11-18 (victor): one Mailgun call to 2 recipients with `recipient-variables` and `h:List-Unsubscribe=<https://www.upiixsol.com/baja?t=%recipient.token%>` delivered `List-Unsubscribe: <…?t=tok-uno>` and `<…?t=tok-dos>` respectively (Gmail "Mostrar original"; SPF, DKIM and DMARC pass for mg.upiixsol.com). So `docs/spikes/mailgun.md` §3 is verified and `UNSUBSCRIBE_HEADER_IN_BATCH` can be on: every campaign goes in batches of ≤ 1 000 with the per-recipient one-click header, instead of one call per recipient below 100 and no header above 100.
- **Depends on:** UPS-091
- **Uses contract:** None
- **Related:** UPS-073, UPS-071
- **Paths:** app/services/mailgun.py, app/tests/test_mailgun.py, docs/spikes/mailgun.md
- **Freeze-Allowed:** no
- **Tests:** test_batch_sends_per_recipient_unsubscribe_header_variable, test_small_audience_also_batches_in_one_call, test_header_points_to_the_api_one_click_url
- **Acceptance:**
  - `UNSUBSCRIBE_HEADER_IN_BATCH = True` (or the switch and the per-recipient fallback removed if nothing else uses them); every send is ≤ 1 000 recipients per call with `h:List-Unsubscribe=<%recipient.unsubscribe_url%>` and `h:List-Unsubscribe-Post`, and the recipient variables carry `unsubscribe_url` (the API URL `/api/mail/unsubscribe?t=…`, so the RFC 8058 one-click POST suppresses and a GET only redirects to `/baja`).
  - `docs/spikes/mailgun.md` §3 changes from "unverified" to "verified 2026-11-18" with the result above (no addresses, no message ids).
  - Tests that assert the old fallback (one call per recipient below 100, no header above 100) change only there; a human runs first: `UAK_HUMAN=victor bash .uak/bin/uak allow UPS-096 --tests --reason 'victor verified the per-recipient List-Unsubscribe in a batch'`.
- **Verify:** `bash .uak/bin/q uv run pytest -q --tb=short -x app/tests/test_mailgun.py app/tests/test_mail_campaigns.py`
- **Next step:** after the human `uak allow`, stubs for the Tests names and `uak red UPS-096`; then flip the switch, then the spike note.
