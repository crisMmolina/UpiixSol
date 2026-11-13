# Spec 002 · UpiixIA route "De cero a LLMs" with sequential video segments
- Status: approved (human, 2026-11-10) · Owner: @crisMmolina · PROJECT principles: 1, 3, 4, 5
- Source: human brief `.uak/ruta-ia-videos.md` (2026-11-10). Content catalog (§5 of the brief) is copied into `docs/spikes/ruta-ia-catalog.md` by UPS-046 and becomes the source of truth for links.

## Problem
UpiixIA only has the demo route "Fundamentos de IA con Python" (`app/fixtures/demo.json`): 2 modules, 4 standalone freeCodeCamp videos that overlap and do not form a sequence. The club needs a real route **from zero to building and using an LLM**, where each lesson picks up exactly where the previous one ended and no lesson is a 10-hour video. Today the player cannot do this: `embed_url()` drops any timestamp, `Lesson` has no start/end, and the admin save path canonicalizes the URL to `watch?v=ID`, discarding `t=`.

## Stories
- As a **member**, I want each lesson of "De cero a LLMs" to play only its segment of a long video, so that I advance class by class without scrubbing.
- As a **member**, I want to know each lesson's language before I press play, so that I turn on subtitles when it is in English.
- As an **academy admin**, I want to set a lesson's start and end (`mm:ss` or `h:mm:ss`), or paste a link with `?t=`, so that I can split long videos myself after the route is loaded.
- As the **club**, I want the route loaded by an idempotent seed step, so that it ships without hand entry and can be re-run safely.

## Acceptance criteria (EARS)
Segments (any lesson):
- When a member opens a lesson with `start_s = 2938` and `end_s = 5665`, the system shall serve an `embed_url` with `?start=2938&end=5665`, and the player shall start at 2938 s and stop at 5665 s.
- When a lesson has only `start_s`, the system shall add only `start`. When it has neither, the embed URL shall be exactly what it is today.
- When an admin pastes `https://youtu.be/Kp4Mvapo5kc?t=850` (also `t=14m10s`, `&start=850`) into the lesson form and start is empty, the UI shall prefill start = `14:10`.
- When an admin saves start/end as `mm:ss` or `h:mm:ss`, the system shall store integer seconds. When both are set, `duration_min` shall be `ceil((end_s − start_s) / 60)`.
- If `end_s ≤ start_s`, or either value is negative or not an integer, the system shall reject the create or update with 422 and a Spanish message, shown in the form's reserved `FormMessage`. On a partial update (PATCH) the check uses the stored value for the field not sent.
- The system shall never put user-supplied URL text into the embed. Only the validated video id and validated integers are used.

Route content:
- When the seed runs, the system shall create the route "De cero a LLMs" in UpiixIA with the 9 modules and their lessons from `app/fixtures/ruta-ia.json`. When it runs again, module and lesson counts shall not change.
- While a lesson's catalog `status` is `verificar` or `buscar`, the system shall keep it unpublished (`is_published = false`).
- The route shall be published from the first seed run. When the seed runs again, it shall never edit a published lesson, never delete anything, and never change the old demo route (open questions 1–3).
- Each lesson description shall end with `*Video en español.*` or `*Video en inglés (activa subtítulos en español).*`.
- New lessons shall appear in the player, count toward progress (completed ÷ published), and "Continuar donde te quedaste" shall behave as today.

Security and permissions:
- `start_s`/`end_s` shall be writable only through the existing lesson endpoints, with the same role × academy scope (no new rows in `docs/permissions-matrix.md`). The permission-matrix test shall cover a write that includes the new fields.

## Non-functional
- Latency: `GET /api/lessons/{id}` and `GET /api/academies/{slug}/home` stay p95 < 300 ms with the new route seeded (about 55 lessons more).
- Pagination: no list endpoint returns more than 50 items (a module with more lessons pages as today).
- Coverage: `app/` stays at 100 %; the migration round-trips on SQLite and Postgres 16 (CI).
- Privacy: the server never fetches YouTube (no SSRF, `docs/spikes/youtube.md`). The embed stays on `youtube-nocookie.com`.
- Accessibility: start/end inputs have visible labels, an `mm:ss` hint, and the error is announced in the `FormMessage`.

## Out of scope
- YouTube Data API (titles, durations, availability checks from the server).
- Ethics/safety (a live club event), the club's own Jetson videos (added later), and the final team project.
- A DB column for lesson language. Language lives only in the description text.
- Changing the old demo route beyond what the human decides (open question 1).

## Open questions
All answered by the human on 2026-11-10 ("OK con tus propuestas").
- [x] 1. Old demo route "Fundamentos de IA con Python": **stays as it is**. The seed does not touch it (tests and e2e depend on it). When the new route is complete, an admin unpublishes the demo route from the panel, which is reversible and needs no code. No `demo_data` DB column is added.
- [x] 2. Route publication: **the route is published from the start**, and only its `ok` lessons are visible. Lessons marked `verificar` or `buscar` stay unpublished, and members already never see unpublished lessons. This replaces the brief's "published only if all lessons are `ok`".
- [x] 3. Re-running the seed: **it creates what is missing** (route, module, lesson, matched by title) and updates the seed-owned fields only of lessons that are still unpublished. It never edits a published lesson and never deletes anything.
- [x] 4. Module 9 (Jetson): **its intro lesson uses an official NVIDIA Jetson video found in UPS-046**, with the tutorials as links. It stays a draft until that video is verified.
- [x] 5. Production: **the content step runs as part of `python -m app.seed`**, which is idempotent. In prod it runs only when a human runs that command (runbook). It creates no accounts beyond what the seed already creates.
