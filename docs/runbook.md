# Runbook · UpiixSol Campus

Operación del stack de producción (UPS-015): `docker-compose.yml` levanta **db** (PostgreSQL 16 con volumen `pgdata`), **api** (FastAPI; aplica migraciones al arrancar) y **nginx** (SPA compilada, `/media` con caché y proxy a `/api`). Solo nginx publica un puerto, y solo en `127.0.0.1`. db y api viven en `backend`, una red interna sin salida a internet; nginx está en `backend` y en `edge`, la red por la que entra el puerto publicado. Los tres corren con `no-new-privileges`.

Todos los comandos se corren desde la raíz del repo en el servidor (p. ej. `/opt/upiixsol`). On-call: @crisMmolina.

## 1. Primer despliegue
1. Requisitos: Docker Engine con Compose v2, el repo clonado y un dominio con TLS delante (§TLS).
2. Configuración: `cp deploy/env.example .env` y llena los valores. Genera cada secreto con `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`:
   - `POSTGRES_PASSWORD`: usa un valor URL-safe, porque va dentro de `DATABASE_URL`.
   - `JWT_SECRET`: al menos 32 caracteres; sin él la API no arranca en prod.
   - `SEED_DEFAULT_PASSWORD`: al menos 12 caracteres y distinto del default documentado; la API rechaza valores débiles.
   - `CORS_ORIGINS`: el origen público, p. ej. `https://campus.example.org`. Nunca `*`.
   - `COOKIE_SECURE=true`: el sitio va detrás de HTTPS.
   - `SEED_ON_START=true` **solo** en este primer arranque.
3. Arranque: `docker compose up -d --build --wait`. La API corre `alembic upgrade head` y, si `SEED_ON_START=true`, el seed idempotente (`SEED_OK ... accounts=6` en `docker compose logs api`).
4. Verifica:
   - `curl -fsS http://127.0.0.1:8080/api/health` → `{"status":"ok"}`.
   - `/api/ready` → `{"status":"ready"}` (la BD responde).
   - `/api/docs` → 404 (en prod la documentación está apagada).
5. Pon `SEED_ON_START=false` en `.env` y rota las contraseñas sembradas (§Seed).

## 2. Actualizar a una versión nueva
1. Haz un respaldo antes de cada actualización (`deploy/backup.sh`) y anota la migración actual: `docker compose run --rm --no-deps -T --entrypoint alembic api current`.
2. `git fetch --tags && git checkout vX.Y.Z`.
3. En `.env`, pon `APP_VERSION=X.Y.Z` para que la imagen anterior siga etiquetada y se pueda hacer rollback.
4. `docker compose up -d --build --wait`. Las migraciones nuevas se aplican solas al arrancar la API.
5. Verifica como en §1.4 y revisa `docker compose logs --since 10m api`.

## 3. Rollback
1. Mira en qué migración está la BD: `docker compose run --rm --no-deps -T --entrypoint alembic api current`.
2. Si la versión nueva trajo migraciones, regresa **con la imagen nueva** (es la que las conoce) a la revisión que anotaste en §2.1: `docker compose run --rm --no-deps -T --entrypoint alembic api downgrade <rev anotada>`. Usa `downgrade -1` solo si la versión trajo exactamente una migración. Desde UPS-084 `alembic downgrade` se niega si el host de la BD no es SQLite ni localhost: en un rollback real contra una BD remota (incluido el host `db` de compose) añade `-e ALEMBIC_ALLOW_REMOTE_DOWNGRADE=yes` a ese único comando (§11). Las migraciones son reversibles (CI corre `upgrade` → `downgrade base` → `upgrade`).
3. Vuelve al código y la imagen anteriores: `git checkout vANTERIOR`, `APP_VERSION=ANTERIOR` en `.env`, y luego `docker compose up -d --wait`. Si la imagen ya no existe, agrega `--build`.
4. Si el downgrade no es posible, restaura el respaldo previo a la actualización (§5).

## 4. Respaldos (RPO 24 h)
- `deploy/backup.sh` genera dos archivos:
  - `db-<UTC>.dump`: `pg_dump --format=custom`, ejecutado dentro del contenedor db, así que la contraseña no sale de él.
  - `media-<UTC>.tar.gz`: las imágenes subidas.

  Escribe primero en `*.partial`: un respaldo fallido nunca parece válido. Borra solo sus propios archivos con más de `KEEP_DAYS` días (default 14). Los archivos quedan con permisos `600`, porque contienen datos personales.
- Variables: `BACKUP_DIR` (default `~/upiixsol-backups`, fuera del clon de git para que un `git add -A` nunca suba dumps) y `KEEP_DAYS`. El directorio y los archivos quedan con permisos solo para el dueño, y una ejecución fallida no deja archivos `*.partial`.
- Cron diario:
  ```
  30 3 * * * cd /opt/upiixsol && deploy/backup.sh >> /var/log/upiixsol-backup.log 2>&1
  ```
- Copia `BACKUP_DIR` fuera del servidor (otro disco o almacenamiento externo). Un respaldo en el mismo disco no protege contra la pérdida del servidor.

## 5. Restaurar (RTO 4 h)
Ensayado en el stack local: borrar datos → restaurar → los datos y `/media` vuelven.
```bash
DUMP=~/upiixsol-backups/db-AAAAMMDDTHHMMSSZ.dump
MEDIA=~/upiixsol-backups/media-AAAAMMDDTHHMMSSZ.tar.gz
docker compose stop api
docker compose exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --single-transaction' < "$DUMP"
docker compose run --rm --no-deps -T --entrypoint tar api -C /data -xzf - < "$MEDIA"
docker compose up -d --wait api
```
Después verifica `/api/ready` y entra con una cuenta real. En un servidor nuevo, primero completa §1 (sin seed) y luego restaura.

## 6. Contraseñas sembradas (Seed)
Las cuentas del seed (`IDEA.md` §2.3) nacen con `must_change_password = true` y la contraseña `SEED_DEFAULT_PASSWORD`. Antes de abrir el sitio:
1. Pon `SEED_ON_START=false` en `.env` y aplica con `docker compose up -d --wait`.
2. Cada dueño entra y cambia su contraseña en Mi cuenta → Seguridad (UPS-014). Con `REQUIRE_PASSWORD_CHANGE=true` (default) la API no deja hacer nada más hasta cambiarla y la web lleva directo a esa pestaña (UPS-020). Por eso el superadmin que va a repartir accesos cambia la suya primero. Para cuentas sin dueño todavía, ese superadmin la restablece desde el panel de usuarios (UPS-009) y entrega la contraseña temporal en persona; la temporal también obliga a cambiarla.
3. Cambia también `SEED_DEFAULT_PASSWORD` en `.env`, para que un seed accidental no use el valor que ya se compartió.

Si se perdió la contraseña inicial antes de que alguien entrara: pon un `SEED_DEFAULT_PASSWORD` nuevo y arranca una vez con `SEED_ON_START=true`. Las cuentas sembradas que nunca se usaron (siguen con contraseña provisional y nadie se la ha cambiado ni restablecido) toman el valor nuevo; las demás no cambian (UPS-031).

### 6.1 Contenido: ruta «De cero a LLMs» de UpiixIA (UPS-047)
La ruta (9 módulos, 65 clases, del catálogo verificado en `docs/spikes/ruta-ia-catalog.md`) **no** se siembra con el seed normal: la agrega un humano cuando quiere publicarla.
- Con Docker Compose: `docker compose exec api python -m app.seed --ruta-ia`.
- En un host con el código y el `.env` de producción: `uv run python -m app.seed --ruta-ia`.

Imprime una línea como `ruta-ia: +9 modules, +65 lessons, 0 updated, 1 drafts`. Es idempotente: correrlo otra vez no duplica nada. Busca ruta, módulos y clases por título, crea lo que falte y solo refresca las clases que siguen en borrador; **nunca** edita una clase publicada (ya es del admin) ni borra nada. Publica solo las clases `ok` del catálogo; la 8.4 (sustituto) queda en borrador hasta que alguien vea el video. La ruta demo «Fundamentos de IA con Python» no se toca: cuando la nueva esté completa, un admin puede despublicarla desde el panel.

## 7. TLS
nginx escucha HTTP en `${HTTP_BIND}:${HTTP_PORT}` (default `127.0.0.1:8080`). Pon delante un terminador TLS **en el mismo host** (nginx o Caddy del sistema con Let's Encrypt) que haga proxy a `http://127.0.0.1:8080`. El hosting de producción sigue sin decidirse (spec 001, preguntas abiertas). El terminador debe:
- Agregar `X-Forwarded-For` con la IP del cliente. nginx usa la **última** dirección de ese encabezado, así que da igual si el terminador sobrescribe o agrega: un valor que mande el cliente nunca se toma.
- Enviar `X-Forwarded-Proto https`.
- Agregar HSTS (`Strict-Transport-Security: max-age=31536000`) y fijar su `server_name` al dominio.

Además: `COOKIE_SECURE=true` y `CORS_ORIGINS=https://<dominio>`.

**Nunca** cambies `HTTP_BIND` a `0.0.0.0`. nginx confía en el `X-Forwarded-For` de todo lo que entra por ese puerto (§8); si el puerto quedara público, cualquiera podría elegir su IP y evadir el rate limit.

## 8. Seguridad del proxy
- **IP del cliente.** Todo lo que entra por el puerto publicado llega a nginx desde el gateway de la red `edge` (`172.31.0.1`), nunca desde el cliente. nginx confía en el `X-Forwarded-For` solo de esa dirección (`set_real_ip_from`), toma la última entrada y se la pasa a uvicorn sobrescribiendo el encabezado. uvicorn corre con `--proxy-headers --forwarded-allow-ips=172.30.0.10`: solo confía en nginx. Nunca `*`, porque el rate limit (5/min/IP en login y registro) se basa en la IP del cliente.
- **Probado en el stack local**, con curl en el papel del terminador:
  - Dos clientes distintos tienen cada uno su propio límite.
  - Un `X-Forwarded-For` inyectado por el cliente antes de la IP real no cambia la llave.
- **Límite de body:** `client_max_body_size 6m`, igual que `app/body_limit.py` (probado: un body de 7 MB → 413).
- **Encabezados:** nginx agrega los mismos encabezados de seguridad que la app (en `/api` oculta los de la app para que no salgan duplicados). `/media` lleva la misma CSP `sandbox`, para que un archivo subido (incluso SVG) no pueda ejecutar scripts.
- **Imágenes:** las base se fijan por tag dentro de ramas con soporte (`nginx:1.30` estable, `postgres:16`, `python:3.12`, `node:24`). Reconstruye (`docker compose build --pull`) al menos una vez al mes para recibir parches.

## 9. Diagnóstico rápido
| Síntoma | Revisa |
|---|---|
| 502 en `/api` | `docker compose ps` (¿api healthy?) y `docker compose logs --tail 100 api` |
| La API no arranca | Un `ValueError` de settings en los logs: falta `JWT_SECRET` o `SEED_DEFAULT_PASSWORD` es débil (§1.2) |
| `/api/ready` → 503 | `docker compose logs db`, espacio en disco, `POSTGRES_PASSWORD` igual en db y api (sale de la misma variable) |
| 429 a todos los usuarios | El rate limit ve una sola IP: el terminador no manda `X-Forwarded-For` o no está en el host (§7, §8) |
| Imágenes 404 tras un deploy | ¿Se recreó el volumen `media`? Restaura `media-*.tar.gz` (§5) |

## 10. Correo (Mailgun)
Activar, probar, retirar y revertir el correo: [docs/mail-mailgun.md](mail-mailgun.md). Rollback inmediato: `MAIL_ENABLED=false`.

## 11. Nunca apuntes el .env local a producción
- **Incidente 2026-11-17:** un agente corrió `alembic upgrade head && alembic downgrade base` (Verify de UPS-072) en un worktree. `wt new` enlaza el `.env` del checkout principal en cada worktree, y su `DATABASE_URL` apuntaba a la base de producción en Neon: el downgrade borró todas las tablas.
- **Recuperación:** restauración a un punto en el tiempo desde el historial de Neon (rama restaurada a justo antes del downgrade y promovida), luego `alembic current` para confirmar la revisión y una prueba rápida de login.
- **Regla:** el `.env` local solo apunta a SQLite o a una base de desarrollo desechable, nunca a producción. Para ida y vuelta de migraciones usa una base temporal: `DATABASE_URL=sqlite:////tmp/rt.db uv run alembic upgrade head && DATABASE_URL=sqlite:////tmp/rt.db uv run alembic downgrade base`.
- **Guarda (UPS-084):** `app/migrations/env.py` rechaza cualquier `downgrade` si la URL no es SQLite y el host no es `localhost`, `127.0.0.1` ni `::1`. Solo se salta con `ALEMBIC_ALLOW_REMOTE_DOWNGRADE=yes` en ese único comando (rollback real, §3). `upgrade` no cambia.
