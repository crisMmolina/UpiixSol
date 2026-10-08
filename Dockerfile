# UpiixSol Campus · multi-stage build (UPS-015, UPS-030). Targets:
#   api    → FastAPI + uvicorn (runs migrations on start, see deploy/entrypoint.sh)
#   web    → nginx serving the built SPA and proxying /api (see deploy/nginx.conf)
#   single → api that also serves the built SPA, one container on $PORT (default target; Render free)
# Build api + web with `docker compose build` (runbook: docs/runbook.md); single: docs/deploy-render.md.

# ── Frontend build ──────────────────────────────────────────
FROM node:24-alpine AS web-build
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

# ── API runtime ─────────────────────────────────────────────
FROM python:3.12-slim AS api
COPY --from=ghcr.io/astral-sh/uv:0.12.18 /uv /bin/uv
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/srv/.venv/bin:$PATH"
WORKDIR /srv
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-install-project
COPY alembic.ini ./
COPY app/ app/
COPY deploy/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 0755 /usr/local/bin/entrypoint.sh \
    && useradd --system --uid 10001 --home-dir /srv app \
    && mkdir -p /data/media && chown app /data/media
USER app
ENV ENV=prod MEDIA_DIR=/data/media
EXPOSE 8000
ENTRYPOINT ["entrypoint.sh"]

# ── nginx (static SPA + reverse proxy) ──────────────────────
# Stable branch, pinned by tag (not digest) so a rebuild picks up its security patches.
FROM nginx:1.30-alpine AS web
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY deploy/security-headers.conf /etc/nginx/snippets/security-headers.conf
COPY --from=web-build /web/dist /usr/share/nginx/html

# ── single container (API + SPA, UPS-030) ───────────────────
# app/main.py serves web/dist when it exists. Last stage, so a plain `docker build .` (Render) builds it.
FROM api AS single
COPY --from=web-build /web/dist /srv/web/dist
