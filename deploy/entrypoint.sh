#!/bin/sh
# API container start (UPS-015): migrate, optionally seed, then serve.
# uvicorn trusts X-Forwarded-For only from nginx's fixed IP (never "*" in compose): the rate limit keys on
# client IP. On Render (UPS-030) only Render's proxy can reach the container, so render.yaml sets "*";
# a client can then spoof the per-IP key, while the per-email login limit still holds (docs/deploy-render.md).
set -eu

# Neon and other hosts hand out postgres:// or postgresql:// URLs; SQLAlchemy needs the psycopg driver named.
case "${DATABASE_URL:-}" in
  postgres://*) DATABASE_URL="postgresql+psycopg://${DATABASE_URL#postgres://}"; export DATABASE_URL;;
  postgresql://*) DATABASE_URL="postgresql+psycopg://${DATABASE_URL#postgresql://}"; export DATABASE_URL;;
esac

alembic upgrade head

if [ "${SEED_ON_START:-false}" = "true" ]; then
  python -m app.seed  # idempotent; refuses the documented default password when ENV=prod
fi

exec uvicorn app.main:app \
  --host 0.0.0.0 --port "${PORT:-8000}" \
  --proxy-headers --forwarded-allow-ips="${FORWARDED_ALLOW_IPS:?set FORWARDED_ALLOW_IPS to the proxy IP}" \
  --no-server-header
