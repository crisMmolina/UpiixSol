#!/bin/sh
# API container start (UPS-015): migrate, optionally seed, then serve.
# uvicorn trusts X-Forwarded-For only from nginx's fixed IP (never "*"): the rate limit keys on client IP.
set -eu

alembic upgrade head

if [ "${SEED_ON_START:-false}" = "true" ]; then
  python -m app.seed  # idempotent; refuses the documented default password when ENV=prod
fi

exec uvicorn app.main:app \
  --host 0.0.0.0 --port 8000 \
  --proxy-headers --forwarded-allow-ips="${FORWARDED_ALLOW_IPS:?set FORWARDED_ALLOW_IPS to the nginx IP}" \
  --no-server-header
