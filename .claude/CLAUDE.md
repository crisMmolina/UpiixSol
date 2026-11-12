# Shared instructions

@../AGENTS.md

Load `.uak/docs/` only when `AGENTS.md` §7 or your mode says so. Minimal context leaves tokens for the task.

## Claude Code only
- Hooks:
  - `SessionStart` already ran `uak next` and showed your inbox.
  - `PostToolUse` sends heartbeats and injects only actionable messages. On Bash, an output over 12k chars reaches you as head + tail (a diff: a per-file index with line ranges) + the path of the full log: read it by ranges (`sed -n`, `grep -n`), or rerun with `UAK_RAW=1` only if you need everything.
  - `Stop` won't let you finish with unhandled messages.
  - `PreToolUse` (`guard`) blocks destructive or publishing commands, even when chained.
  - `UserPromptSubmit` blocks pasted secrets.
  - The status line shows task, 5 h/7 d plan usage and `uak pace`; when the pace level changes, a hook tells you once.
- Commands:
  - All modes: `/uak-setup`, `/uak-plan`, `/uak-start`, `/uak-loop`, `/uak-advise`, `/uak-ship`, `/uak-review`, `/uak-handoff`, `/uak-secure`, `/uak-retro`, `/uak-design-lock`.
  - sprint: `/uak-demo`.
  - marathon: `/uak-spec`.
- Subagents (isolated context, summary only):
  - `uak-scout` (Haiku): read-only lookups.
  - `uak-runner` (Haiku): tests, smoke, app.
  - `uak-reviewer`: reviews.
  - `design-critic`: UI screenshots against DESIGN.md (every mode).
  - `security-reviewer` (Opus): marathon sensitive PRs.
  - `uak-architect` (Opus): checkpoints only.
  - `Explore`: only when uak-scout is not enough (it runs on the lead model, so it is pricier).
- Orchestration (`.uak/docs/ORCHESTRATION.md`):
  - You are the Sonnet lead. Send `uak-scout` (Haiku) for any lookup needing 3 or more searches, up to 3 in parallel on disjoint questions. Do one-search lookups yourself.
  - Consult the Opus advisor only at the 3 checkpoints: plan lock (more than 2 files or a contract), the same failure twice, done on risky diffs. If the advisor tool is missing or the session is long, use `/uak-advise <plan|stuck|done>` instead.
  - Never fan out Opus subagents. The `guard agent` hook caps parallel subagents and the Opus budget per session, scaled by `uak pace` (surge 2×, conserve ½, critical 1 and no Opus).
- Run tests with `bash .uak/bin/q ...`, using pytest `-q --tb=short -x`. Edit with Edit; never rewrite whole files.
- Avoid editing `AGENTS.md` or `CLAUDE.md` while agents are running: it invalidates every agent's prompt cache. Urgent amendments go through `uak decision`.

# Project · UpiixSol Campus
Club platform (IPN · UPIIZ): academies, learning routes with progress, community channels, role panels. Product: `IDEA.md` · spec: `docs/specs/001-campus/` · permission matrix: `docs/permissions-matrix.md` · ADRs: `docs/adr/`. UI and docs in Spanish (Mexico).

## Commands
- Setup: `uv sync` · `npm --prefix web ci` · `uv run alembic upgrade head` (copy `.env.example` → `.env`, fill `JWT_SECRET`, `SEED_DEFAULT_PASSWORD`).
- Run: `uv run uvicorn app.main:app --reload --port $UAK_PORT` (docs at `/api/docs`) · `npm --prefix web run dev` (Vite reads `$UAK_PORT+1`).
- Backend: `uv run ruff check app` · `uv run pytest --cov=app` (target 100 %, CI floor 90) · one test: `bash .uak/bin/q uv run pytest -q --tb=short -x app/tests/test_learning.py::test_name`.
- Migrations must round-trip (CI): `uv run alembic upgrade head && uv run alembic downgrade base`. CI also runs pytest on PostgreSQL 16: no SQLite-only SQL.
- Web: `npm --prefix web run lint` (oxlint) · `npm --prefix web run build` (`tsc -b` + vite).
- E2E (Playwright, outside default `testpaths`): `npm --prefix web run build && uv run pytest e2e` — serves `web/dist` on a fresh seeded SQLite DB, at 1280 and 390 wide; screenshots in `e2e/artifacts/`.
- Everything: `bash .uak/bin/smoke`.

## Architecture
- Auto-discovery, so nobody edits `app/main.py` or `web/src/App.tsx`: a router is `app/routers/<f>.py` exporting `router = APIRouter(prefix="/api/...")`; a screen is `web/src/features/<f>/index.tsx` exporting `routes` (optional `order`); root providers in `web/src/lib/providers.tsx`.
- Backend layers per feature: `routers/` (HTTP, deps, pagination) → `services/` (queries, rules, `AppError`) → `models/` (SQLAlchemy 2) + `schemas/` (Pydantic).
- Authorization in `app/security.py`: `current_user`, `require_role(...)`, `ensure_academy_scope(user, academy_id)`. Always take `academy_id` from the DB row, never the request body. Every endpoint is covered by `app/tests/test_permissions_matrix.py`.
- Errors: `raise AppError(status, "msg")` → `{"error": {"code","message","details"}}`. Lists use `app/pagination.py` cursor pages (≤ 50 items).
- Tests: `app/tests/conftest.py` gives each test an empty in-memory DB; fixtures `seeded`, `as_superadmin`, `as_admin_ia`, `as_member` load the demo seed.
- Frontend: shared UI in `web/src/components/`, layouts in `web/src/layouts/`, API client and types in `web/src/lib/`; design rules in `web/DESIGN.md`; brand assets in `assets/brand/` used as-is.
- Shared-file owners: `.uak/OWNERS.md` — check it before editing `pyproject.toml`, `app/config.py`, migration env and similar.
- UI numbers come from DB queries, never an LLM. Commits carry no AI co-author lines.

## When compacting
Keep only: ID, branch, worktree, exact next step, pending criteria, failures with exact errors, verify commands, decisions and unanswered inbox. Drop command output, diffs and explorations.
