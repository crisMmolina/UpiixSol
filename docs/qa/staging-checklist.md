# Checklist de staging · Render + Neon (UPS-059)

Registro de las pruebas de despliegue y de la puerta P0-06 / P0-07 de `docs/PRUEBAS-CAMPUS.md`.

**Regla de este documento:** cada resultado viene de una ejecución real, con fecha, comando y salida. Lo que no se pudo ejecutar dice por qué. Las pruebas DEP-01…DEP-05 requieren una cuenta de Render y de Neon y gastar en ellas, así que quedan como checklist para que las ejecute un humano; no tienen resultado.

Estados: `OK` (ejecutada, salida real registrada) · `FALLA` (ejecutada, no cumple lo esperado) · `pendiente: lo ejecuta un humano` (no ejecutada por el agente).

## Resumen

| ID | Prueba | Estado | Fecha (2026-11-12, hora local UTC-6) |
|---|---|---|---|
| P0-06 | Migraciones en SQLite | OK | 21:53 |
| P0-06 | Migraciones en Postgres 16 | OK | 21:55 |
| P0-07 | `docker compose up` desde cero (sin volúmenes) | OK | 21:57 – 22:04 |
| DEP-01 | Deploy limpio en staging (Render + Neon) | pendiente: lo ejecuta un humano | — |
| DEP-02 | Cold start de Render (servicio dormido) | pendiente: lo ejecuta un humano | — |
| DEP-03 | Las imágenes subidas sobreviven a un redeploy | pendiente: lo ejecuta un humano | — |
| DEP-04 | Deep link `/a/x/clases/1` al recargar en producción | pendiente: lo ejecuta un humano | — |
| DEP-05 | Backup y restore de Neon | pendiente: lo ejecuta un humano | — |

Entorno de las ejecuciones: Windows 11 Enterprise 10.0.26200, Git Bash, uv 0.13.7, Docker 29.3.1 con Compose v5.1.1, Node 24.14.1. Rama `feat/ups-059` a partir de `c54df7e` (main).

---

## P0-06 · Migraciones (SQLite y Postgres 16)

**Migraciones en el repo:** 7 archivos en `app/migrations/versions/`: `0001_initial`, `0002_password_changed_at`, `0003_one_reaction_per_user`, `0004_media_objects`, `0005_activity_events`, `0006_site_settings`, `0007_lesson_segments`. La spec de P0-06 dice "0001 a 0006"; la 0007 (UPS-045) ya existe y también se probó. Ver hallazgo H1.

Comando de la tarea (Verify), ejecutado tal cual en la raíz del worktree:

```
uv run alembic upgrade head && uv run alembic downgrade base && uv run alembic upgrade head
```

### SQLite (por defecto, `DATABASE_URL=sqlite:///./upiixsol.db`)

- Fecha: 2026-11-12 21:53 (UTC-6). Base de datos vacía (`upiixsol.db` no existía).
- Comando: el Verify de arriba.
- Resultado real: exit 0. Se ejecutaron 21 pasos de migración (7 subidas, 7 bajadas, 7 subidas). `uv run alembic current` → `0007 (head)`.

### Postgres 16

- Fecha: 2026-11-12 21:54 – 21:55 (UTC-6).
- Base: contenedor desechable `ups059-pg16`, imagen `postgres:16-alpine` (Postgres 16.16), en `127.0.0.1:55959`, usuario y base `upiixsol`. Se eliminó al final.
- Comandos:
  ```
  export DATABASE_URL="postgresql+psycopg://upiixsol:<clave-de-prueba>@127.0.0.1:55959/upiixsol"
  uv run alembic upgrade head && uv run alembic downgrade base && uv run alembic upgrade head
  docker exec ups059-pg16 psql -U upiixsol -d upiixsol -tAc "select version_num from alembic_version"
  ```
- Resultado real: exit 0. 21 pasos de migración. `alembic current` → `0007 (head)`. `alembic_version` → `0007`.

---

## P0-07 · `docker compose up` desde cero (sin volúmenes)

- Fecha: 2026-11-12 21:56 (build) · 21:57 (up) · 22:02 (comprobaciones) · 22:04 (limpieza), UTC-6.
- Aislamiento: proyecto de Compose `ups059qa` con `-p` (el `docker-compose.yml` fija `name: upiixsol`, así que sin `-p` chocaría con el stack principal). Puerto publicado `HTTP_PORT=8695`. Contenedores, volúmenes y redes son solo de `ups059qa`.
- Las imágenes no quedan aisladas por `-p`: `docker-compose.yml` fija las etiquetas `upiixsol-api:${APP_VERSION:-latest}` y `upiixsol-web:${APP_VERSION:-latest}`. El `build` asignó esas etiquetas a las imágenes nuevas; si ya existían imágenes con esas etiquetas en la máquina, siguen existiendo, pero la etiqueta `latest` apunta ahora a las de esta prueba. No se borró ninguna imagen. Ver H4.
- `.env` temporal, con secretos generados localmente y sin commitear (ignorado por git); se borró al terminar. Valores para local: `COOKIE_SECURE=false` y `CORS_ORIGINS=http://127.0.0.1:8695`, porque la prueba va por HTTP local; en producción van `true` y el dominio https.

Comandos y resultados:

1. `HTTP_PORT=8695 docker compose -p ups059qa build` → exit 0; imágenes `upiixsol-api:latest` y `upiixsol-web:latest`.
2. `HTTP_PORT=8695 docker compose -p ups059qa up -d --wait --wait-timeout 420` → exit 0. `api`, `db` y `nginx` quedan `healthy` (`docker compose ps`).
3. `docker compose -p ups059qa logs api` →
   - `Running upgrade  -> 0001, initial` … `Running upgrade 0006 -> 0007, lessons: optional video segment start_s/end_s (UPS-045)`
   - `SEED_OK academy_id=1 accounts=6`
   - `Uvicorn running on http://0.0.0.0:8000`
4. Comprobaciones a través de nginx (`curl`):
   - `GET /api/health` → 200, `{"status":"ok"}`
   - `GET /api/ready` → 200, `{"status":"ready"}`
   - `GET /api/docs` → 404 (documentación apagada en prod, como dice `docs/runbook.md` §1.4)
   - `GET /a/x/clases/1` → 200, `text/html` (SPA)
   - `docker compose -p ups059qa exec -T db psql ... "select count(*) from users"` → 6
5. Limpieza: `HTTP_PORT=8695 docker compose -p ups059qa down -v` → exit 0; se eliminaron los volúmenes `ups059qa_pgdata` y `ups059qa_media` y las redes `ups059qa_backend` y `ups059qa_edge`. Sin contenedores ni volúmenes `ups059*` restantes.

**Resultado P0-07: OK** (la app levanta, el seed corre y `/api/ready` responde ok).

---

## DEP-01 · Deploy limpio en staging

Estado: **pendiente: lo ejecuta un humano.** El agente no creó cuentas, no desplegó y no llamó a ninguna URL de Render.

Precondiciones: cuenta de Neon (plan free) y cuenta de Render (plan free); autorización explícita del responsable para crear ambas cuentas y desplegar.

**Staging, no producción:** usar un proyecto de Neon de staging y un servicio de Render de staging con nombre distinto del de producción (el `render.yaml` trae el nombre `upiixsol`; cámbialo en el Blueprint, p. ej. `upiixsol-staging`). **Nunca** reutilizar la `DATABASE_URL` de producción. `SEED_ON_START=true` solo debe apuntar a la base de staging: contra una base de producción volvería a crear el contenido de demostración.

Pasos:
1. Neon: crear el proyecto de **staging** en AWS us-east-2. Con **Connection pooling apagado**, copiar la cadena directa (el host no lleva `-pooler`) y guardarla como secreto. No pegarla en chats, issues ni el repo.
2. Render: **New → Blueprint** → repo `crisMmolina/UpiixSol`, rama `main` (lee `render.yaml`). Pegar `DATABASE_URL` con la cadena de Neon y dar **Apply**.
3. En Render → **Logs** del servicio, buscar las migraciones y el seed.
4. Desde una terminal (sustituir `<servicio>` por la URL del servicio de **staging**):
   ```
   curl -s https://<servicio>/api/health
   curl -s https://<servicio>/api/ready
   ```

Esperado:
- En los logs aparecen `Running upgrade ... 0007` y `SEED_OK academy_id=1 accounts=6` (sin tener que correr nada a mano).
- `/api/health` → `{"status":"ok"}`; `/api/ready` → `{"status":"ready"}`.
- `/api/docs` → 404.

Registro (llenar al ejecutar): fecha __ · URL de staging __ · salida de `curl` __ · resultado `OK` / `FALLA`.

---

## DEP-02 · Cold start de Render (servicio dormido)

Estado: **pendiente: lo ejecuta un humano.**

Precondiciones: DEP-01 en `OK`, sobre el servicio de **staging** (`<servicio>` = staging, nunca producción). Esperar al menos 15 minutos sin visitas al servicio (plan free: se duerme).

Pasos:
1. Abrir `https://<servicio>/` en una ventana de incógnito, con la consola de DevTools abierta. Anotar la hora de la primera petición y la hora en que se ve la pantalla de inicio.
2. Medir también el API: `curl -s -o /dev/null -w "%{http_code} %{time_total}s\n" https://<servicio>/api/health` después de otro periodo de reposo.
3. Revisar la consola y la pestaña Red: sin errores de UI (ni `500`, ni pantalla de error, ni `Failed to fetch`).

Esperado: la primera carga termina en menos de 60 s, sin error visible en la UI ni en la consola.

Registro: fecha __ · tiempo de primera carga __ s · errores en consola __ · resultado __.

---

## DEP-03 · Las imágenes subidas sobreviven a un redeploy

Estado: **pendiente: lo ejecuta un humano.**

Precondiciones: DEP-01 en `OK`, sobre el servicio de **staging** (nunca producción). En staging, `render.yaml` fija `MEDIA_STORAGE=database`: las imágenes van a la tabla `media_objects` en Neon, no al disco (el disco del plan free se borra en cada reinicio). Ver hallazgo H2.

Pasos:
1. Iniciar sesión en staging con una cuenta de prueba (la contraseña temporal la da el superadmin; ver `docs/deploy-render.md` §3-4) y subir una imagen (avatar, portada o foto de blog).
2. En Neon (SQL editor, solo lectura): `select count(*) from media_objects;` → anotar el número `N1`.
3. Anotar la URL de la imagen (`/media/<tipo>/<archivo>.webp`) y confirmar `200` con `curl -sI https://<servicio>/media/<tipo>/<archivo>.webp`.
4. Render → servicio de **staging** (no el de producción) → **Manual Deploy → Deploy latest commit**. Esperar a que quede `Live`.
5. Repetir el `curl` del paso 3 y el conteo del paso 2.

Esperado: la imagen sigue respondiendo `200` con `Content-Type: image/webp` después del redeploy; `count(*)` no baja (`N2 >= N1`).

Registro: fecha __ · URL de la imagen __ · `curl` antes __ · `curl` después __ · `N1` __ · `N2` __ · resultado __.

---

## DEP-04 · Deep links en producción (`/a/x/clases/1` al recargar)

Estado: **pendiente: lo ejecuta un humano.**

Precondiciones: DEP-01 en `OK`, sobre el servicio de **staging** (`<servicio>` = staging, nunca producción).

Pasos:
1. En una pestaña nueva, escribir directamente `https://<servicio>/a/x/clases/1` (no navegar desde la portada) y dar Enter.
2. Con la sesión iniciada, recargar la página (F5) y repetir en `https://<servicio>/cuenta`.
3. Desde terminal:
   ```
   curl -s -o /dev/null -w "%{http_code} %{content_type}\n" https://<servicio>/a/x/clases/1
   ```

Esperado: `200 text/html`, y la SPA se monta (no aparece una página 404 ni un JSON `{"error": ...}`). Una ruta bajo `/api/` desconocida sí responde JSON 404; eso no es esta prueba.

Registro: fecha __ · salida de `curl` __ · resultado __.

---

## DEP-05 · Backup y restore de Neon

Estado: **pendiente: lo ejecuta un humano.**

Precondiciones: DEP-01 en `OK`. Restaurar **nunca** sobre la base de producción: usar un proyecto o rama de prueba de Neon.

Qué dice la documentación: `docs/deploy-render.md` §5 documenta el respaldo con `pg_dump` sobre la cadena directa de Neon. `docs/runbook.md` §4-5 documenta `deploy/backup.sh` y el restore con `pg_restore` dentro del contenedor `db`, que no aplica a Neon. Ver hallazgo H3.

Pasos (respaldo):
1. Copiar la cadena directa de Neon del proyecto de staging.
2. `pg_dump "<cadena directa>" -Fc -f upiixsol-$(date +%F).dump`
3. Guardar el archivo fuera del repo (`git status` no debe mostrarlo), con permisos solo para el dueño (`chmod 600`).

Pasos (restore, en un proyecto o rama de prueba de Neon):
4. `pg_restore --clean --if-exists --no-owner --single-transaction -d "<cadena del proyecto de prueba>" upiixsol-<fecha>.dump`
5. Comprobar: `select count(*) from users;` (debe dar el mismo número que el origen) y `select count(*) from media_objects;`.
6. Apuntar una instancia de la app a esa base (o usar la misma app de staging con esa cadena en una prueba aparte) y comprobar `/api/ready` → `{"status":"ready"}` y el inicio de sesión con una cuenta sembrada.

Esperado: el dump se crea sin error; el restore termina con exit 0; los conteos coinciden; `/api/ready` responde ok y la cuenta entra.

Registro: fecha __ · tamaño del dump __ · exit de `pg_restore` __ · conteos origen/destino __ · resultado __.

---

## Hallazgos (no corregidos aquí: cada uno es una tarea nueva o un `uak followup`)

- **H1 · Número de migraciones.** `docs/PRUEBAS-CAMPUS.md` §0 (P0-06) dice "0001 a 0006"; el repo tiene 0001…0007 (`0007_lesson_segments`, UPS-045). La prueba se ejecutó con las 7. Corregir el texto de P0-06.
- **H2 · Expectativa de DEP-03 desactualizada.** `docs/PRUEBAS-CAMPUS.md` §15 dice "El `MEDIA_DIR` es persistente (disco o almacenamiento externo)". El despliegue real (`render.yaml`, `docs/deploy-render.md`) usa `MEDIA_STORAGE=database`. La expectativa debe decir eso.
- **H3 · Sin procedimiento de restore para Neon.** `docs/runbook.md` §5 solo describe el restore con `docker compose` (contenedor `db`), y `docs/deploy-render.md` §5 solo describe el `pg_dump`. Falta el restore de Neon documentado. DEP-05 usa los pasos de este documento hasta que exista.
- **H4 · Informativo, no se registra como bug (diseño intencional).** `docker-compose.yml` fija `name: upiixsol` y etiquetas de imagen fijas (`upiixsol-api:latest`, `upiixsol-web:latest`). Sin `-p` dos stacks en la misma máquina chocan en contenedores, volúmenes y redes; las imágenes con etiqueta fija se comparten entre stacks, como pasó en esta prueba (ver P0-07). Usar `-p` y `APP_VERSION` distinto para pruebas paralelas.

**Estado de los hallazgos:** H1, H2 y H3 no se corrigieron en esta tarea (fuera de sus Paths). `uak followup UPS-031` no se pudo usar porque `.uak/PROJECT.md` tiene `Plan-Channel` distinto de `claims` y el CLI pide un PR que añada la tarea a `.uak/TASKS.md`. Se avisó al humano con `uak msg human --kind request` (mensaje #401) para que decida si crea las tareas.
