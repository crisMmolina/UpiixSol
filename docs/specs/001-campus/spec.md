# Spec 001 · UpiixSol Campus v1
- Status: draft · Owner: @crisMmolina · PROJECT principles: 1, 2, 4, 5, 6
- Source of truth for product detail: `IDEA.md` (§2 roles, §4 flow, §5 core, §6 data, §9 scope). This spec only adds testable criteria.

## Problem
Club members have their material scattered across WhatsApp, Drive, YouTube and Discord, with no progress tracking and no per-academy identity. Delivery is due Thursday 8 Oct 2026, followed by daily use during the semester.

## Stories
- As a **member**, I want to register with my boleta and resume the exact lesson where I left off, so that I keep moving forward without hunting for links.
- As a **member**, I want to post in my academy's channel, so that I can share findings with my community.
- As an **academy admin**, I want to edit only my academy (identity, routes, modules, lessons, resources, events), so that I can prepare the week's content without touching others.
- As a **superadmin**, I want to create academies with their own branding and admins, so that the club grows without code changes.

## Acceptance criteria (EARS)
- When a visitor submits name, a 10-digit boleta, an email and a password, the system shall create a `member` and start a session; if the boleta or email already exists, the system shall respond 409 without revealing which account owns it.
- When any role logs in through the single login, the system shall redirect by role (member → campus home, academy_admin → their academy's panel, superadmin → admin panel).
- If there are more than 5 login or registration attempts per minute from one IP, the system shall respond 429.
- When a member opens an academy, the UI shall apply that academy's CSS variables (`--academy-*`) and logo, and its home shall show "Continuar" pointing to the first unfinished published lesson, with % = completed ÷ published lessons computed on the server.
- When a member marks a lesson completed, the system shall persist `lesson_progress`, and after a reload the % shall stay the same.
- If an academy_admin calls any write endpoint of another academy, the system shall respond 403 (verified in the backend; hiding the button is not enough).
- If a member calls any admin write endpoint, the system shall respond 403; an unauthenticated user shall get 401.
- When a superadmin creates an academy, the system shall create its community channel in the same transaction.
- When a superadmin changes a user's role (`PUT /api/admin/users/{id}/role`, UPS-093, spec 005), the system shall allow only `member` ⇄ `academy_admin` of an active club, shall refuse `superadmin` as a target or as the new role and any change to their own role, and the new scope shall apply on that user's next request (ROL-07); the only way to change a role is that endpoint, `PATCH /api/admin/users/{id}` keeps rejecting `role`.
- While a list is requested, the system shall return at most 50 items plus a `next_cursor`.
- When a post or description containing HTML/JS is saved, the system shall store and render it sanitized (no script execution).
- If an uploaded image is not png/jpg/webp/svg by its real type, or exceeds 2 MB (logos) / 5 MB (posts), the system shall respond 422; uploaded SVGs are sanitized or served with a restrictive CSP.
- When a YouTube URL (watch, youtu.be, shorts, embed) is saved, the system shall store `youtube_video_id`; if the URL is invalid, it shall respond 422; if the video fails to load, the player shall show "Video no disponible" without breaking the layout.
- While the community is visible, the UI shall refresh posts every 30 s (no realtime).
- When an admin hides a post, the system shall record who hid it and when.
- In the community, the system shall expose only the nickname and avatar, never the boleta or email.

## Non-functional
See `.uak/PROJECT.md` NFRs: p95 < 300 ms on academy home and lesson, ≤ 50 items per page, coverage target of 100 %, < 250 KB gzip of initial JS, WCAG AA contrast on brand colors, responsive (player sidebar becomes a drawer on mobile), UI in Spanish (Mexico).

## Out of scope
Payments, certificates, exams, realtime chat, DMs, email notifications, password recovery by email, native app, dark mode.

## Open questions
- [ ] Exact IPN boleta format (10 digits assumed) · @crisMmolina
- [ ] Real videos for the UpiixIA route · UpiixIA admin
- [ ] Can members propose gallery projects? (v1: no) · @crisMmolina
- [ ] Production hosting · @crisMmolina
