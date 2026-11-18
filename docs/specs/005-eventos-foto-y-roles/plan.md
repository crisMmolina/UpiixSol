# Plan 005 · Event photo and role assignment

## Design
Event photo (mirrors the blog and gallery cover flow, no new pattern)
- `POST /api/events/{event_id}/cover` (multipart `file`) and `DELETE /api/events/{event_id}/cover`, both behind the existing `Manager` dependency (`superadmin`, `academy_admin`) and the existing `_get_event(db, event_id, user)` scope check.
- `app/services/events.py` gets `replace_cover` and `remove_cover` like `app/services/blog.py`: `media.save_upload(file, "cover")` first, set `cover_url`, `db.commit()`, and only then `media.delete_media(previous)`.
- `delete_event` also removes the cover media after the commit (today it would leave it orphaned).
- Web: the form in `web/src/features/events/index.tsx` gets the "Foto del evento" field; `EventOut` in `web/src/lib/types.ts` gets `cover_url`; cards use the same `/media/` check as the blog (`startsWith("/media/")`).

Role assignment
- `PUT /api/admin/users/{user_id}/role` in `app/routers/admin.py` (superadmin only, like every route in that file) with `RoleChangeIn {role: member | academy_admin, academy_id: int | None}` in `app/schemas/users.py`. A dedicated route keeps `PATCH /api/admin/users/{id}` closed to `role` (the mass-assignment guard in `InModel` and its tests stay untouched).
- `app/services/admin.py: change_role(db, actor, user_id, data)` holds every rule; the router only parses and commits.
- Web: the Usuarios tab in `web/src/features/superadmin/index.tsx` gets the role badge, the two actions and the confirmation dialog (shared `Overlay`).

## Data and migrations
None. Both features use existing columns.

## Contracts
- `POST /api/events/{event_id}/cover` → `EventOut`; `DELETE /api/events/{event_id}/cover` → `EventOut` (cover_url null).
- `PUT /api/admin/users/{user_id}/role` body `{"role": "academy_admin", "academy_id": 3}` → `UserAdminOut`.
- Both are new write endpoints, so the permission matrix (`MATRIX`) and `docs/permissions-matrix.md` grow in the same task that adds them.

## Threat model (STRIDE)
| Threat | Vector | Mitigation | Test |
|---|---|---|---|
| Elevation of privilege | Member or club admin calls the role endpoint | `require_role(Role.superadmin)` on the admin router; matrix row for the 5 roles | matrix row for the 5 roles (`test_permissions_matrix.py`) |
| Elevation of privilege | Body smuggles `superadmin` or another club | enum limited to `member` and `academy_admin`; `academy_id` validated against active clubs from the DB | rejects_superadmin_role_and_missing_or_inactive_club_with_422 |
| Elevation of privilege | Club admin uploads to another club's event | scope from the DB row via `_get_event` | academy_admin_cannot_touch_the_cover_of_another_club_or_a_global_event |
| Tampering | Superadmin removes the last superadmin or locks themselves out | targets that are superadmins are refused (409); self-change refused (409) | refuses_own_role_and_superadmin_targets_with_409 |
| Tampering / XSS | SVG or script disguised as an event photo | `cover` kind does not allow SVG; real type from the bytes; re-encode; media served with sandbox CSP | rejects_svg_fake_image_and_oversized_cover |
| Denial of service | Huge or many uploads | 5 MB cap per file plus the global request body limit | rejects_svg_fake_image_and_oversized_cover |
| Information disclosure | Role endpoint or event payload leaks emails | `UserAdminOut` is superadmin only (already); `EventOut` adds only `cover_url` | event_payload_carries_cover_url_and_no_personal_data |
| Repudiation | Nobody knows who promoted whom | structured log line with actor, target, old and new role, no PII | new_role_applies_on_next_request_and_logs_without_pii |

## Observability
One structured log line per role change (`role.changed`, actor id, target id, old, new). Existing access log already records the upload route and status.

## Rollout and rollback
Both ship in one deploy each, no flag and no migration, so rollback is redeploying the previous image. A wrongly promoted user is fixed with the same endpoint (`member`). Orphan media from a failed upload cannot appear because the old file is deleted only after the commit.

## Cost
No new dependency, no new service. Stored photos count against the Neon storage of the free plan (≤ 5 MB each, re-encoded to WebP, usually far less).

## Tasks
- UPS-093 · Superadmin turns members into club admins and back (P0). Goes first: the club needs more admins now, and it owns the shared permission-matrix files.
- UPS-094 · Photo on events: upload, replace, remove and show (P0). Depends on UPS-093 only because both add rows to `app/tests/test_permissions_matrix.py` and `docs/permissions-matrix.md`.
