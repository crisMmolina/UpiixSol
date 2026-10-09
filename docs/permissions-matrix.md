# Matriz de permisos (escritura)

Generado por `uv run python -m app.tests.test_permissions_matrix` desde `MATRIX` en `app/tests/test_permissions_matrix.py`; el test verifica cada celda contra el backend (IDEA §2.1).

Cobertura: **57/57 endpoints de escritura (100 %)** × 5 roles.

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
| POST | `/api/channels/{channel_id}/posts` | 🔒 | ✅ | ✅ | ✅ | ✅ |  |
| POST | `/api/posts/{post_id}/comments` | 🔒 | ✅ | ✅ | ✅ | ✅ |  |
| POST | `/api/posts/{post_id}/hide` | 🔒 | ❌ | ✅ | ❌ | ✅ | moderation: academy channel |
| POST | `/api/comments/{comment_id}/hide` | 🔒 | ❌ | ✅ | ❌ | ✅ | moderation: academy channel |
| PUT | `/api/posts/{post_id}/reactions/{kind}` | 🔒 | ✅ | ✅ | ✅ | ✅ | idempotent, 60/min per user (UPS-018) |
| DELETE | `/api/posts/{post_id}/reactions/{kind}` | 🔒 | ✅ | ✅ | ✅ | ✅ | idempotent (UPS-018) |
| POST | `/api/events` | 🔒 | ❌ | ✅ | ❌ | ✅ |  |
| PATCH | `/api/events/{event_id}` | 🔒 | ❌ | ✅ | ❌ | ✅ |  |
| DELETE | `/api/events/{event_id}` | 🔒 | ❌ | ✅ | ❌ | ✅ |  |
| POST | `/api/lessons/{lesson_id}/complete` | 🔒 | ✅ | ✅ | ✅ | ✅ | any signed-in user (enrolls on first progress) |
| DELETE | `/api/lessons/{lesson_id}/complete` | 🔒 | ✅ | ✅ | ✅ | ✅ |  |
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

## Lecturas sensibles

`READ_MATRIX`: lecturas con borradores o datos personales (correo, boleta), verificadas igual que las escrituras.

| Método | Ruta | Anónimo | Miembro | Admin (su club) | Admin (otro club) | Superadmin | Nota |
|---|---|---|---|---|---|---|---|
| GET | `/api/academies/{academy_id}/content` | 🔒 | ❌ | ✅ | ❌ | ✅ | drafts included |
| GET | `/api/academies/{academy_id}/enrollments` | 🔒 | ❌ | ✅ | ❌ | ✅ | email and boleta of each enrollee |
| GET | `/api/admin/academies` | 🔒 | ❌ | ❌ | ❌ | ✅ | inactive clubs included |
| GET | `/api/admin/users` | 🔒 | ❌ | ❌ | ❌ | ✅ |  |
| GET | `/api/admin/home` | 🔒 | ❌ | ❌ | ❌ | ✅ |  |
