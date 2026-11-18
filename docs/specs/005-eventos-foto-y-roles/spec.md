# Spec 005 · Event photo and role assignment by the superadmin
- Status: draft, requested by the human (cris) 2026-11-17 · PROJECT principles: 1, 2, 4, 5
- Two small, independent features. Neither adds a dependency.

## Problem
1. An event has a `cover_url` column and every event card reserves room for it, but nothing can set it: the event form has no image field and the API has no upload route. Announcements for events (like the first class) go out with plain text.
2. A superadmin can only **create** a new account as `academy_admin` (`POST /api/admin/users`). There is no way to turn an **existing** member into an admin, and the club needs more admins now (UPS-066 was dropped on 2026-11-12 on purpose, "the superadmin does not change user roles for now"; this spec reverses that decision for the club-admin role only, by the human's request on 2026-11-17).

## Stories
- As a **superadmin** or **club admin**, I want to attach a photo when I publish an event, replace it later and remove it, so that the calendar, the club page and the home show the event with an image.
- As a **superadmin**, I want to make an existing member an admin of a club, and turn an admin back into a member, so that the club can add admins without creating new accounts.

## Acceptance criteria (EARS)
Event photo
- When a manager uploads an image for an event, the system shall store it as kind `cover` (same rules as blog and gallery covers: real type from the bytes, ≤ 5 MB, ≤ 1600 px, re-encoded), set `events.cover_url` and return the updated event.
- If the file is not a real image or is over the limit, the system shall respond 422 or 413 with the existing media error and leave the event unchanged.
- While the caller is an `academy_admin`, the system shall allow the upload, replacement and removal only for events of their own club (`users.academy_id` against the event row, never the request); another club's event or a global event gives 403; a `member` gets 403 and an anonymous caller 401.
- When a cover is replaced or removed, or an event is deleted, the system shall delete the old media only after the database commit (no orphan on failure, no broken image on success).
- The event form (create and edit) shall offer "Foto del evento" with a preview, accept PNG, JPG or WebP, and on create send the event first and then the photo; if the photo fails the event stays published and the form says "El evento se publicó, pero la foto no se pudo subir. Intenta de nuevo."
- The calendar list, the club page and the home shall show the photo when `cover_url` exists and the current layout without it otherwise, with a decorative `alt=""` (the title is already text).

Role assignment
- When a superadmin calls `PUT /api/admin/users/{user_id}/role` with `academy_admin` and an active `academy_id`, the system shall set the role and the club of that user and return the user.
- When a superadmin sets `member`, the system shall set the role and clear `academy_id`, and the user shall stay enrolled where they already were.
- The system shall only allow `member` and `academy_admin` in v1: `superadmin` is refused with 422 (same rule as `POST /api/admin/users`), and a target that is already a `superadmin` is refused with 409, so the last superadmin can never be removed.
- If the superadmin targets their own account, the system shall respond 409 ("No puedes cambiar tu propio rol.").
- If the club does not exist or is inactive, or `academy_id` is missing for `academy_admin`, the system shall respond 422; if the user does not exist, 404; an inactive user, 409.
- Every other role (`academy_admin`, `member`) gets 403 and an anonymous caller 401 on that endpoint; the permission matrix and `docs/permissions-matrix.md` list it.
- The new role shall apply on the very next request (the role is read from the database on each call), and a demoted admin shall lose access to the club panel at once.
- The Usuarios panel shall show each user's role and, for a superadmin, a "Hacer admin de un club" action with a club picker and a "Quitar admin" action, each behind a confirmation dialog naming the person and the club.

## Non-functional
- No new table or migration: `events.cover_url`, `users.role` and `users.academy_id` already exist.
- Role changes are logged as a structured line with the actor id, target id and the old and new role, no email or name.

## Out of scope
- Promoting anyone to `superadmin` (stays a manual operation).
- Several photos per event, cropping, drag and drop, alt text editing.
- Bulk role changes and an audit-log screen.

## Decisions (cris 2026-11-17: use the defaults)
1. A demoted club admin keeps no new access: the history of campaigns they sent stays as it is (the sender stays on the campaign) and new sends need the role. [Decided]
2. Promoting to `superadmin` is not in v1; it stays a manual operation. [Decided]
