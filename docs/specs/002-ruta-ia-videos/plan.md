# Plan 002 · UpiixIA route "De cero a LLMs" with sequential video segments
Spec: [`spec.md`](spec.md) (approved 2026-11-10) · Spike for links: `docs/spikes/ruta-ia-catalog.md` (UPS-046).

## Design
There are two independent parts, joined by one contract (the lesson fields `start_s` and `end_s`).

1. **Video segments.** Segments are added to lessons generally, not built only for this route.
   - `app/services/youtube.py` gains two functions:
     - `parse_start(url) -> int | None` reads `t=`/`start=` in the query or fragment, in the forms `850`, `850s`, `14m10s` and `1h2m3s`. It returns `None` for anything else, and it parses the string only (no fetch).
     - `embed_url(video_id, start_s=None, end_s=None)` builds `?start=&end=` with `urlencode` from ints that have already been validated.

     `extract_video_id` is unchanged.
   - Admin save path (`app/services/academy_admin.py`): `create_lesson` and `update_lesson` take `start_s`/`end_s`.
     - If `start_s` is not sent and the URL carries a time, `parse_start` runs **before** `_canonical()` drops the query, so the server prefills too, not only the UI.
     - `end_s > (start_s or 0)` is checked on the merged values, so a PATCH that sends only one field is checked against the stored one.
     - `duration_min` is derived when both values exist, and an explicit `duration_min` is ignored in that case.
   - Read path (`app/services/learning.py`): `LessonOut.embed_url` comes from `embed_url(id, start_s, end_s)`, and `start_s`/`end_s` are also exposed so the "Ver en YouTube" link can add `&t=`.
   - Web:
     - `playerSrc()` (`web/src/features/learning/youtube.ts`) merges parameters through `new URL()` instead of appending `?…`. Today it would produce `…?start=1?enablejsapi=1`.
     - The admin lesson form adds Inicio and Fin fields (`mm:ss` or `h:mm:ss`). A pure `parseClock`/`formatClock` helper converts between that text and seconds. Pasting a URL with `t=` prefills Inicio when it is empty.
     - Errors go to the existing reserved `FormMessage`.

   **Why columns on `lessons`** rather than a separate `lesson_segments` table: a lesson has exactly one segment. The columns are nullable and additive, so old lessons need no change. A table would add a join to the hot `GET /api/lessons/{id}` path for no gain.

   **Why server-side `embed_url`** rather than having the web add `start`/`end`: there is one place that builds embed URLs from validated ints, and both the web and tests read the same value.

2. **Route content.**
   - `app/fixtures/ruta-ia.json` uses the `route` shape of `demo.json` plus `start_s`, `end_s`, `lang` (`es`/`en`) and `status` (`ok`/`verificar`/`buscar`) per lesson, and an optional `note` (for example the 2015 scikit-learn caveat).
   - `app/seed.py` gains `seed_ruta_ia(db)`, called from `seed()` after the academy exists and **outside** the `has_content` guard, so it also runs on databases that already have the demo route.
   - Matching is by title: route (academy, title), then module (route, title), then lesson (module, title).
   - Create: the route is published. A lesson is published when `status == ok`, otherwise it is a draft. `duration_min` is derived from the segment. The language suffix is appended to the description, which then goes through `clean_markdown`.
   - Update: only lessons that are still unpublished get the seed-owned fields refreshed (url, id, segment, description, links, position, published flag from status). Published lessons are left alone. Nothing is deleted.
   - `buscar` rows have no URL yet, so they are **not** created. They live in the spike document until UPS-046 fills them in, because `youtube_url` is required.

   **Why a JSON fixture plus the seed** rather than an admin import endpoint: it needs no new write surface (no new permission-matrix rows, no upload parsing), and the human brief asks for it. Admins edit afterwards in the existing panel.

No ADR: everything here is additive and cheap to reverse (nullable columns, a reversible migration, a fixture). It follows ADR 0001's stack and auth unchanged.

## Data and migrations
- `0007_lesson_segments.py` (expand only, reversible) adds two columns with `batch_alter_table` so SQLite works:
  - `lessons.start_s INTEGER NULL`
  - `lessons.end_s INTEGER NULL`
  - `CHECK (start_s IS NULL OR start_s >= 0)`
  - `CHECK (end_s IS NULL OR end_s > COALESCE(start_s, 0))`

  Downgrade drops the checks, then the columns. No backfill: existing lessons keep NULL, which means the whole video, exactly as today. No contract phase is needed.
- The model mirrors the checks in `Lesson.__table_args__`, so tests built with `create_all` enforce them too.
- CI already runs `alembic upgrade head && downgrade base` on SQLite and `upgrade → downgrade → upgrade` on Postgres 16.

## Contracts
Additive, no version bump. Old clients ignore the new fields.

| Endpoint | Change |
|---|---|
| `POST /api/modules/{id}/lessons`, `PATCH /api/lessons/{id}` (academy-admin routers) | `LessonIn` / `LessonUpdateIn` gain `start_s: int \| None` (0–86 400) and `end_s: int \| None` (1–86 400). 422 `invalid_segment` "El fin del tramo debe ser mayor que el inicio." |
| Lesson admin output (`LessonAdminOut`) | adds `start_s`, `end_s` |
| `GET /api/lessons/{id}` (`LessonOut`) | adds `start_s`, `end_s`; `embed_url` may now carry `?start=&end=` |
| `web/src/lib/types.ts` | `Lesson` / admin lesson types gain `start_s: number \| null`, `end_s: number \| null` |

Consumers:
- `web/src/features/learning/Player.tsx` and `youtube.ts`, because `embed_url` can now contain a query.
- `web/src/features/academy-admin/index.tsx`, the form.
- `e2e/`.

UPS-045 sends `uak msg impact:UPS-045 --kind contract` before it pushes.

## Threat model (STRIDE)
This touches user-supplied URLs that end up in an iframe `src`, an area the spike already treats as sensitive.

| Threat | Vector | Mitigation | Test |
|---|---|---|---|
| Spoofing | Someone other than an admin sets segments | Existing lesson endpoints keep `require_role` and `ensure_academy_scope` | permission matrix: a write with `start_s`/`end_s` by a member or another club's admin gets 403 |
| Tampering | `?t=` or `start` carrying script or extra params (`t=1&autoplay=1`, `javascript:`) into the embed | `parse_start` returns only an `int`. `embed_url` builds the query from ints with `urlencode`, and the stored URL stays canonical `watch?v=ID` | `test_youtube`: hostile `t` values give `None`, and the embed equals the expected string exactly |
| Repudiation | Who changed a segment | Same as other lesson edits: access log with user id | n/a (unchanged) |
| Information disclosure | The embed leaks the viewer to YouTube | Embed stays on `youtube-nocookie.com`, no server fetch | existing `test_youtube` |
| Denial of service | Huge numbers or long `t` strings | Pydantic bounds (≤ 86 400), `t` regex anchored with a length cap, `youtube_url` max 300 | bounds tests (422) |
| Elevation of privilege | Seed run by a non-human path | The seed is a CLI only, with no endpoint | n/a |

## Observability
- No new logs or metrics: lesson views and completions are already captured by `analytics.capture` and the access log (no PII).
- The seed prints a one-line summary: `ruta-ia: +N modules, +N lessons, N updated, N drafts`.

## Rollout and rollback
- No flag. Segments are inert until a lesson has `start_s` or `end_s`.
- Order:
  1. UPS-045 (API) merges first.
  2. UPS-048 (web) follows. Until it lands, the old `playerSrc` would break segmented embeds, so **no lesson gets a segment in prod before UPS-048 merges**. The seed task UPS-047 depends on both.
- Promotion: the e2e for lesson 1.2 passes and a human opens 3 segmented lessons on a phone.
- Rollback:
  - Content: unpublish the route from the panel (instant).
  - Code: revert the PR. The migration downgrade is safe because the columns are nullable and nothing else reads them.

## Cost
Zero infrastructure or API cost: no YouTube API, no new services. About 55 more `lessons` rows.

## Risks
- **Completion on segment end:** completion relies on the iframe's `ended` state (UPS-024). The `end` parameter should stop playback with state 0, but this is **unverified**. UPS-048 checks it in a real browser and records the result. If `ended` does not fire, the fallback is to treat `paused` within 2 s of `end_s` as ended, which is a decision for that task.
- **Link rot:** catalog rows are checked once in UPS-046. Lessons that are not `ok` stay drafts.

## Tasks
Each task starts with a failing test (`uak red`).

| ID | What | Depends on | Uses contract |
|---|---|---|---|
| UPS-045 | API: segments in model, migration 0007, youtube helpers, admin save, lesson output | None | None |
| UPS-046 | Spike: verify and complete the catalog (`verificar`/`buscar`), chapter timestamps for modules 5 and 7 | None | None |
| UPS-048 | Web: player merges embed params, Inicio/Fin in the admin form, prefill from `?t=`, check `ended` at `end` | UPS-045 | UPS-045 |
| UPS-047 | Seed "De cero a LLMs" from `ruta-ia.json` (idempotent, drafts for non-`ok`), e2e lesson 1.2 | UPS-045, UPS-048 | UPS-046 |
