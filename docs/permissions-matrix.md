# Matriz de permisos (escritura)

Generado por `uv run python -m app.tests.test_permissions_matrix` desde `MATRIX` en `app/tests/test_permissions_matrix.py`; el test verifica cada celda contra el backend (IDEA §2.1).

Cobertura: **72/72 endpoints de escritura (100 %)** × 5 roles.

✅ permitido · ❌ 403 · 🔒 401 (sin sesión) · 🌐 público

| Método | Ruta | Anónimo | Miembro | Admin (su club) | Admin (otro club) | Superadmin | Nota |
|---|---|---|---|---|---|---|---|
| POST | `/api/auth/register` | 🌐 | 🌐 | 🌐 | 🌐 | 🌐 | rate-limited per IP |
| POST | `/api/auth/login` | 🌐 | 🌐 | 🌐 | 🌐 | 🌐 | rate-limited per IP |
| POST | `/api/auth/refresh` | 🌐 | 🌐 | 🌐 | 🌐 | 🌐 | refresh cookie + X-Requested-With |
| POST | `/api/auth/logout` | 🌐 | 🌐 | 🌐 | 🌐 | 🌐 | refresh cookie + X-Requested-With |
| POST | `/api/academies/{slug}/enroll` | 🔒 | ✅ | ✅ | ✅ | ✅ |  |
| DELETE | `/api/academies/{slug}/enroll` | 🔒 | ✅ | ✅ | ✅ | ✅ |  |
| PATCH | `/api/academies/{academy_id}/branding` | 🔒 | ❌ | ✅ | ❌ | ✅ |  |
| POST | `/api/academies/{academy_id}/logo` | 🔒 | ❌ | ✅ | ❌ | ✅ |  |
| POST | `/api/academies/{academy_id}/mascot` | 🔒 | ❌ | ✅ | ❌ | ✅ |  |
| POST | `/api/academies/{academy_id}/routes` | 🔒 | ❌ | ✅ | ❌ | ✅ |  |
| PUT | `/api/academies/{academy_id}/routes/order` | 🔒 | ❌ | ✅ | ❌ | ✅ |  |
| PATCH | `/api/routes/{route_id}` | 🔒 | ❌ | ✅ | ❌ | ✅ |  |
| DELETE | `/api/routes/{route_id}` | 🔒 | ❌ | ✅ | ❌ | ✅ |  |
| POST | `/api/academies/{academy_id}/routes/{route_id}/modules` | 🔒 | ❌ | ✅ | ❌ | ✅ |  |
| PUT | `/api/routes/{route_id}/modules/order` | 🔒 | ❌ | ✅ | ❌ | ✅ |  |
| PATCH | `/api/modules/{module_id}` | 🔒 | ❌ | ✅ | ❌ | ✅ |  |
| DELETE | `/api/modules/{module_id}` | 🔒 | ❌ | ✅ | ❌ | ✅ |  |
| POST | `/api/modules/{module_id}/lessons` | 🔒 | ❌ | ✅ | ❌ | ✅ |  |
| PUT | `/api/modules/{module_id}/lessons/order` | 🔒 | ❌ | ✅ | ❌ | ✅ |  |
| PATCH | `/api/lessons/{lesson_id}` | 🔒 | ❌ | ✅ | ❌ | ✅ |  |
| DELETE | `/api/lessons/{lesson_id}` | 🔒 | ❌ | ✅ | ❌ | ✅ |  |
| POST | `/api/academies/{academy_id}/enrollments` | 🔒 | ❌ | ✅ | ❌ | ✅ |  |
| DELETE | `/api/academies/{academy_id}/enrollments/{user_id}` | 🔒 | ❌ | ✅ | ❌ | ✅ |  |
| POST | `/api/admin/academies` | 🔒 | ❌ | ❌ | ❌ | ✅ |  |
| PATCH | `/api/admin/academies/{academy_id}` | 🔒 | ❌ | ❌ | ❌ | ✅ |  |
| POST | `/api/admin/users` | 🔒 | ❌ | ❌ | ❌ | ✅ |  |
| PATCH | `/api/admin/users/{user_id}` | 🔒 | ❌ | ❌ | ❌ | ✅ |  |
| POST | `/api/admin/users/{user_id}/reset-password` | 🔒 | ❌ | ❌ | ❌ | ✅ |  |
| PUT | `/api/admin/home` | 🔒 | ❌ | ❌ | ❌ | ✅ |  |
| PUT | `/api/admin/site` | 🔒 | ❌ | ❌ | ❌ | ✅ |  |
| POST | `/api/admin/site/logo` | 🔒 | ❌ | ❌ | ❌ | ✅ |  |
| POST | `/api/admin/site/mascot` | 🔒 | ❌ | ❌ | ❌ | ✅ |  |
| DELETE | `/api/admin/site/logo` | 🔒 | ❌ | ❌ | ❌ | ✅ | no logo → the name as a three-color wordmark |
| DELETE | `/api/admin/site/mascot` | 🔒 | ❌ | ❌ | ❌ | ✅ | no mascot anywhere |
| POST | `/api/channels/{channel_id}/posts` | 🔒 | ✅ | ✅ | ❌ | ✅ | club channel: its members and admins (UPS-035); General: anyone |
| POST | `/api/posts/{post_id}/comments` | 🔒 | ✅ | ✅ | ✅ | ✅ |  |
| POST | `/api/posts/{post_id}/hide` | 🔒 | ❌ | ✅ | ❌ | ✅ | moderation: academy channel |
| POST | `/api/comments/{comment_id}/hide` | 🔒 | ❌ | ✅ | ❌ | ✅ | moderation: academy channel |
| PUT | `/api/posts/{post_id}/reactions/{kind}` | 🔒 | ✅ | ✅ | ✅ | ✅ | idempotent, 60/min per user (UPS-018) |
| DELETE | `/api/posts/{post_id}/reactions/{kind}` | 🔒 | ✅ | ✅ | ✅ | ✅ | idempotent (UPS-018) |
| POST | `/api/events` | 🔒 | ❌ | ✅ | ❌ | ✅ |  |
| PATCH | `/api/events/{event_id}` | 🔒 | ❌ | ✅ | ❌ | ✅ |  |
| DELETE | `/api/events/{event_id}` | 🔒 | ❌ | ✅ | ❌ | ✅ |  |
| POST | `/api/lessons/{lesson_id}/complete` | 🔒 | ✅ | ✅ | ✅ | ✅ | any signed-in user (enrolls on first progress) |
| POST | `/api/projects` | 🔒 | ❌ | ❌ | ❌ | ✅ |  |
| PUT | `/api/projects/{project_id}` | 🔒 | ❌ | ❌ | ❌ | ✅ |  |
| DELETE | `/api/projects/{project_id}` | 🔒 | ❌ | ❌ | ❌ | ✅ |  |
| POST | `/api/projects/{project_id}/cover` | 🔒 | ❌ | ❌ | ❌ | ✅ |  |
| POST | `/api/blog` | 🔒 | ❌ | ❌ | ❌ | ✅ |  |
| PUT | `/api/blog/{blog_id}` | 🔒 | ❌ | ❌ | ❌ | ✅ |  |
| DELETE | `/api/blog/{blog_id}` | 🔒 | ❌ | ❌ | ❌ | ✅ |  |
| POST | `/api/blog/{blog_id}/cover` | 🔒 | ❌ | ❌ | ❌ | ✅ |  |
| POST | `/api/academies/{academy_id}/resources` | 🔒 | ❌ | ✅ | ❌ | ✅ |  |
| PATCH | `/api/resources/{resource_id}` | 🔒 | ❌ | ✅ | ❌ | ✅ |  |
| DELETE | `/api/resources/{resource_id}` | 🔒 | ❌ | ✅ | ❌ | ✅ |  |
| POST | `/api/resources/{resource_id}/file` | 🔒 | ❌ | ✅ | ❌ | ✅ |  |
| PATCH | `/api/account/profile` | 🔒 | ✅ | ✅ | ✅ | ✅ |  |
| POST | `/api/account/avatar` | 🔒 | ✅ | ✅ | ✅ | ✅ |  |
| POST | `/api/account/email` | 🔒 | ✅ | ✅ | ✅ | ✅ | also requires the current password |
| POST | `/api/account/password` | 🔒 | ✅ | ✅ | ✅ | ✅ | also requires the current password |
| POST | `/api/analytics/events` | 🔒 | ✅ | ✅ | ✅ | ✅ | usage analytics, 30/min per user (UPS-037) |
| DELETE | `/api/posts/{post_id}` | 🔒 | ✅ | ❌ | ❌ | ❌ | author only; moderators hide instead |
| DELETE | `/api/comments/{comment_id}` | 🔒 | ✅ | ✅ | ❌ | ✅ | author, or the moderators of its channel (UPS-070) |
| POST | `/api/mail/audience/preview` | 🔒 | ❌ | ✅ | ❌ | ✅ | superadmin: any audience; academy_admin: own club, its enrollees and outside addresses |
| POST | `/api/mail/test` | 🔒 | ❌ | ✅ | ✅ | ✅ | only to the caller's own address |
| POST | `/api/mail/campaigns` | 🔒 | ❌ | ✅ | ❌ | ✅ | draft; same audience scope as the preview |
| POST | `/api/mail/images` | 🔒 | ❌ | ✅ | ✅ | ✅ | UPS-088: email image (PNG/JPEG copy under /media/mail); rate-limited per user |
| POST | `/api/mail/campaigns/{campaign_id}/send` | 🔒 | ❌ | ✅ | ❌ | ✅ | the campaign's sender or superadmin |
| POST | `/api/mail/campaigns/{campaign_id}/resume` | 🔒 | ❌ | ✅ | ❌ | ✅ | the campaign's sender or superadmin |
| POST | `/api/mail/unsubscribe` | 🌐 | 🌐 | 🌐 | 🌐 | 🌐 | token in ?t=, same 200 for unknown tokens; rate-limited per IP |
| POST | `/api/mail/webhooks/mailgun` | 🌐 | 🌐 | 🌐 | 🌐 | 🌐 | HMAC signature is the credential; really signed payloads in test_mail_webhooks.py |
| PUT | `/api/mail/preferences` | 🔒 | ✅ | ✅ | ✅ | ✅ | the caller's own address only |

## Lecturas sensibles

`READ_MATRIX`: lecturas con borradores o datos personales (correo, boleta), verificadas igual que las escrituras.

| Método | Ruta | Anónimo | Miembro | Admin (su club) | Admin (otro club) | Superadmin | Nota |
|---|---|---|---|---|---|---|---|
| GET | `/api/academies/{academy_id}/content` | 🔒 | ❌ | ✅ | ❌ | ✅ | drafts included |
| GET | `/api/academies/{academy_id}/enrollments` | 🔒 | ❌ | ✅ | ❌ | ✅ | email and boleta of each enrollee |
| GET | `/api/admin/academies` | 🔒 | ❌ | ❌ | ❌ | ✅ | inactive clubs included |
| GET | `/api/admin/users` | 🔒 | ❌ | ❌ | ❌ | ✅ |  |
| GET | `/api/admin/home` | 🔒 | ❌ | ❌ | ❌ | ✅ |  |
| GET | `/api/mail/status` | 🔒 | ❌ | ✅ | ✅ | ✅ | daily quota (UPS-074) |
| GET | `/api/mail/recipients` | 🔒 | ❌ | ✅ | ✅ | ✅ | own club's enrollees and co-admins; email only for superadmin |
| GET | `/api/mail/campaigns` | 🔒 | ❌ | ✅ | ✅ | ✅ | history: superadmin all, academy_admin own club (UPS-075) |
| GET | `/api/mail/campaigns/{campaign_id}` | 🔒 | ❌ | ✅ | ❌ | ✅ | a campaign of the club (UPS-075) |
