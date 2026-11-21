#!/usr/bin/env bash
# UPS-060 · carga local contra la app en Docker, con los límites del plan free de Render.
#   bash perf/run_local.sh USERS DURATION      (ej.: bash perf/run_local.sh 20 60s)
#
# Levanta Postgres 16 y la imagen `api` del Dockerfile (migra y siembra al arrancar) en contenedores
# nuevos de esta corrida; la app corre con `--cpus $LOAD_CPUS --memory $LOAD_MEM` (0.1 CPU, 512 MB por
# defecto, como Render free). Luego corre Locust en modo headless contra $UAK_PORT.
# Sale con 1 si el error rate pasa de 1 % o el p95 pasa de 1500 ms (lo decide perf/locustfile.py).
#
# Entorno de carga (solo en los contenedores de esta prueba, dicho en docs/qa/load-report.md):
#   RATELIMIT_ENABLED=false     los 20-200 usuarios salen de la misma IP: el límite de 5/min tiraría los logins
#   REQUIRE_PASSWORD_CHANGE=false   las cuentas del seed traen contraseña provisional
#   COOKIE_SECURE=false         Locust sobre http no envía cookies Secure del refresh
#
# Variables: LOAD_CPUS (0.1) · LOAD_MEM (512m) · LOAD_SPAWN_RATE (USERS/5) · LOAD_OUT (<git-dir>/load-results)
# Nunca apunta a staging ni producción: solo habla con localhost:$UAK_PORT.
set -euo pipefail

USERS="${1:?uso: bash perf/run_local.sh USERS DURATION (ej. 20 60s)}"
DURATION="${2:?uso: bash perf/run_local.sh USERS DURATION (ej. 20 60s)}"
if [ -z "${UAK_PORT:-}" ]; then
  echo "run_local: UAK_PORT no está definido; entra al worktree de la tarea (wt new / wt session)." >&2
  exit 2
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOAD_CPUS="${LOAD_CPUS:-0.1}"
LOAD_MEM="${LOAD_MEM:-512m}"
SPAWN_RATE="${LOAD_SPAWN_RATE:-$(( USERS / 5 > 0 ? USERS / 5 : 1 ))}"
OUT="${LOAD_OUT:-$(git -C "$ROOT" rev-parse --git-dir)/load-results}"  # fuera del árbol: no entra al commit
RUN="upx-load-${UAK_PORT}-$$"
NET="$RUN-net"
DB="$RUN-db"
APP="$RUN-app"
mkdir -p "$OUT"
STATS_LOG="$OUT/docker-stats-$USERS.log"
: > "$STATS_LOG"

# Secretos de esta corrida: aleatorios, solo viven en el entorno del proceso.
export PG_PASS SEED_DEFAULT_PASSWORD JWT_SECRET LOAD_SEED_PASSWORD
PG_PASS="$(openssl rand -hex 16)"
SEED_DEFAULT_PASSWORD="$(openssl rand -hex 16)"
LOAD_SEED_PASSWORD="$SEED_DEFAULT_PASSWORD"
JWT_SECRET="$(openssl rand -hex 32)"

SAMPLER_PID=""
cleanup() {
  [ -n "$SAMPLER_PID" ] && kill "$SAMPLER_PID" 2>/dev/null || true
  docker stop "$APP" "$DB" >/dev/null 2>&1 || true
  docker network rm "$NET" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "run_local: USERS=$USERS DURATION=$DURATION CPUS=$LOAD_CPUS MEM=$LOAD_MEM port=$UAK_PORT"
docker build --target api -t upiixsol-api:load "$ROOT" >"$OUT/build-$USERS.log" 2>&1 \
  || { echo "run_local: docker build falló (ver $OUT/build-$USERS.log)" >&2; exit 1; }

docker network create "$NET" >/dev/null
docker run -d --rm --name "$DB" --network "$NET" \
  -e POSTGRES_USER=upiixsol -e POSTGRES_DB=upiixsol -e POSTGRES_PASSWORD="$PG_PASS" \
  postgres:16-alpine >/dev/null
for _ in $(seq 1 60); do
  docker exec "$DB" pg_isready -U upiixsol -d upiixsol >/dev/null 2>&1 && break
  sleep 2
done
sleep 3  # postgres:16 arranca un servidor temporal durante initdb; esperamos al definitivo

docker run -d --rm --name "$APP" --network "$NET" \
  -p "127.0.0.1:$UAK_PORT:8000" --cpus "$LOAD_CPUS" --memory "$LOAD_MEM" \
  -e DATABASE_URL="postgresql+psycopg://upiixsol:$PG_PASS@$DB:5432/upiixsol" \
  -e JWT_SECRET -e SEED_DEFAULT_PASSWORD \
  -e SEED_ON_START=true -e FORWARDED_ALLOW_IPS=127.0.0.1 \
  -e RATELIMIT_ENABLED=false -e REQUIRE_PASSWORD_CHANGE=false -e COOKIE_SECURE=false \
  upiixsol-api:load >/dev/null

ready=""
for _ in $(seq 1 90); do
  if curl -fsS "http://127.0.0.1:$UAK_PORT/api/ready" >/dev/null 2>&1; then ready=1; break; fi
  sleep 2
done
if [ -z "$ready" ]; then
  echo "run_local: la app no quedó lista; logs:" >&2
  docker logs "$APP" 2>&1 | tail -30 >&2
  exit 1
fi

# Muestreo de RAM y CPU de la app durante la corrida (para la columna RAM del reporte).
( while true; do
    docker stats --no-stream --format '{{.Container}} {{.MemUsage}} {{.CPUPerc}}' "$APP" >> "$STATS_LOG" 2>/dev/null || true
    sleep 5
  done ) &
SAMPLER_PID=$!

set +e
LOAD_USERS="$USERS" LOAD_DURATION="$DURATION" uvx locust -f "$ROOT/perf/locustfile.py" --headless \
  -u "$USERS" -r "$SPAWN_RATE" \
  --host "http://127.0.0.1:$UAK_PORT" --only-summary \
  --csv "$OUT/ramp-$USERS" --csv-full-history
LOCUST_RC=$?
set -e

kill "$SAMPLER_PID" 2>/dev/null || true
SAMPLER_PID=""
echo "run_local: resultados en $OUT/ramp-${USERS}_stats.csv y $STATS_LOG"
exit "$LOCUST_RC"
