# Runbook · UpiixSol Campus

Operación del stack de producción (UPS-015): `docker-compose.yml` levanta **db** (PostgreSQL 16 con volumen `pgdata`), **api** (FastAPI; aplica migraciones al arrancar) y **nginx** (SPA compilada, `/media` con caché y proxy a `/api`). Solo nginx publica un puerto; db y api quedan en la red interna.

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
1. Haz un respaldo antes de cada actualización: `deploy/backup.sh`.
2. `git fetch --tags && git checkout vX.Y.Z`.
3. En `.env`, pon `APP_VERSION=X.Y.Z` para que la imagen anterior siga etiquetada y se pueda hacer rollback.
4. `docker compose up -d --build --wait`. Las migraciones nuevas se aplican solas al arrancar la API.
5. Verifica como en §1.4 y revisa `docker compose logs --since 10m api`.

## 3. Rollback
1. Mira en qué migración está la BD: `docker compose run --rm --no-deps -T --entrypoint alembic api current`.
2. Si la versión nueva trajo una migración, deshazla **con la imagen nueva** (es la que conoce esa migración): `docker compose run --rm --no-deps -T --entrypoint alembic api downgrade -1`. Las migraciones son reversibles (CI corre `upgrade` → `downgrade base` → `upgrade`).
3. Vuelve al código y la imagen anteriores: `git checkout vANTERIOR`, `APP_VERSION=ANTERIOR` en `.env`, y luego `docker compose up -d --wait`. Si la imagen ya no existe, agrega `--build`.
4. Si el downgrade no es posible, restaura el respaldo previo a la actualización (§5).

## 4. Respaldos (RPO 24 h)
- `deploy/backup.sh` genera dos archivos:
  - `db-<UTC>.dump`: `pg_dump --format=custom`, ejecutado dentro del contenedor db, así que la contraseña no sale de él.
  - `media-<UTC>.tar.gz`: las imágenes subidas.

  Escribe primero en `*.partial`: un respaldo fallido nunca parece válido. Borra solo sus propios archivos con más de `KEEP_DAYS` días (default 14). Los archivos quedan con permisos `600`, porque contienen datos personales.
- Variables: `BACKUP_DIR` (default `./backups`) y `KEEP_DAYS`.
- Cron diario:
  ```
  30 3 * * * cd /opt/upiixsol && deploy/backup.sh >> /var/log/upiixsol-backup.log 2>&1
  ```
- Copia `BACKUP_DIR` fuera del servidor (otro disco o almacenamiento externo). Un respaldo en el mismo disco no protege contra la pérdida del servidor.

## 5. Restaurar (RTO 4 h)
Ensayado en el stack local: borrar datos → restaurar → los datos y `/media` vuelven.
```bash
DUMP=backups/db-AAAAMMDDTHHMMSSZ.dump
MEDIA=backups/media-AAAAMMDDTHHMMSSZ.tar.gz
docker compose stop api
docker compose exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --single-transaction' < "$DUMP"
docker compose run --rm --no-deps -T --entrypoint tar api -C /data -xzf - < "$MEDIA"
docker compose up -d --wait api
```
Después verifica `/api/ready` y entra con una cuenta real. En un servidor nuevo, primero completa §1 (sin seed) y luego restaura.

## 6. Contraseñas sembradas (Seed)
Las cuentas del seed (`IDEA.md` §2.3) nacen con `must_change_password = true` y la contraseña `SEED_DEFAULT_PASSWORD`. Antes de abrir el sitio:
1. Pon `SEED_ON_START=false` en `.env` y aplica con `docker compose up -d --wait`.
2. Cada dueño entra y cambia su contraseña en Mi cuenta → Seguridad (UPS-014). Para cuentas sin dueño todavía, un superadmin la restablece desde el panel de usuarios (UPS-009) y entrega la contraseña temporal en persona.
   *Sin verificar en este runbook: UPS-009 y UPS-014 no estaban integradas cuando se escribió (7 oct 2026).*
3. Cambia también `SEED_DEFAULT_PASSWORD` en `.env`, para que un seed accidental no use el valor que ya se compartió.

## 7. TLS
nginx escucha HTTP en `${HTTP_BIND}:${HTTP_PORT}` (default `127.0.0.1:8080`). Pon delante un terminador TLS del host (nginx o Caddy del sistema con Let's Encrypt) que haga proxy a ese puerto. El hosting de producción sigue sin decidirse (spec 001, preguntas abiertas). Con TLS activo:
- `COOKIE_SECURE=true` y `CORS_ORIGINS=https://<dominio>`.
- El terminador debe **sobrescribir** `X-Forwarded-For` con la IP real del cliente; el nginx del stack la vuelve a sobrescribir con la IP que ve. Si el terminador vive fuera del stack, el rate limit verá la IP del terminador: en ese caso, hay que agregar `set_real_ip_from <IP del terminador>; real_ip_header X-Forwarded-For;` en `deploy/nginx.conf`.

## 8. Seguridad del proxy
- uvicorn corre con `--proxy-headers --forwarded-allow-ips=172.30.0.10`: solo confía en el nginx del stack, que tiene IP fija en la red `internal`. Nunca `*`, porque el rate limit (5/min/IP en login y registro) se basa en la IP del cliente.
- nginx sobrescribe `X-Forwarded-For` con `$remote_addr`: un cliente no puede elegir su llave de rate limit. Probado: 7 logins con `X-Forwarded-For` falsos distintos → 429 al llegar al límite.
- `client_max_body_size 6m`, igual que `app/body_limit.py` (probado: un body de 7 MB → 413).
- nginx agrega los mismos encabezados de seguridad que la app. `/media` lleva la misma CSP `sandbox`, para que un archivo subido (incluso SVG) no pueda ejecutar scripts.

## 9. Diagnóstico rápido
| Síntoma | Revisa |
|---|---|
| 502 en `/api` | `docker compose ps` (¿api healthy?) y `docker compose logs --tail 100 api` |
| La API no arranca | Un `ValueError` de settings en los logs: falta `JWT_SECRET` o `SEED_DEFAULT_PASSWORD` es débil (§1.2) |
| `/api/ready` → 503 | `docker compose logs db`, espacio en disco, `POSTGRES_PASSWORD` igual en db y api (sale de la misma variable) |
| 429 a todos los usuarios | El rate limit ve una sola IP: revisa §7 (`set_real_ip_from`) |
| Imágenes 404 tras un deploy | ¿Se recreó el volumen `media`? Restaura `media-*.tar.gz` (§5) |
