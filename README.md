# UpiixSol Campus

> Tu club, tus academias, un solo campus.

Plataforma del club UpiixSol (IPN · UPIIZ): academias con identidad propia, rutas de aprendizaje con progreso, comunidad por canales y paneles por rol. Producto: [`IDEA.md`](IDEA.md) · Spec: [`docs/specs/001-campus/`](docs/specs/001-campus/spec.md) · Backlog: [`.uak/TASKS.md`](.uak/TASKS.md).

## Stack
FastAPI + SQLAlchemy 2 + Alembic + Pydantic (`app/`) · React 19 + Vite + TypeScript + Tailwind v4 (`web/`) · PostgreSQL (prod/CI), SQLite (dev). Decisiones: [`docs/adr/`](docs/adr/).

## Desarrollo
Requisitos: [uv](https://docs.astral.sh/uv/) y Node 24. Copia `.env.example` a `.env` y llena `JWT_SECRET` y `SEED_DEFAULT_PASSWORD`.

```bash
uv sync
npm --prefix web ci
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000    # API → http://localhost:8000/api/docs
npm --prefix web run dev                             # Web → http://localhost:8001
```

En un worktree de uak usa `$UAK_PORT` (API) y `$UAK_PORT+1` (web): `vite.config.ts` ya los lee.

## Producción (detrás de nginx)
Corre uvicorn con `--proxy-headers --forwarded-allow-ips=<IP del proxy>` (nunca `*`): el rate limit usa la IP del cliente. Detalle en UPS-015 / `docs/runbook.md`.

## Pruebas
```bash
uv run ruff check app
uv run pytest --cov=app        # meta de cobertura: 100 %
npm --prefix web run lint && npm --prefix web run build
bash .uak/bin/smoke            # todo lo anterior + escaneo de secretos
```

## Convenciones
- Un endpoint nuevo = `app/routers/<f>.py` con `router = APIRouter(prefix="/api/...")`; `app/main.py` lo descubre solo.
- Una pantalla nueva = `web/src/features/<f>/index.tsx` exportando `routes`; `web/src/App.tsx` la descubre sola.
- Proveedores raíz (auth, tema) = `web/src/lib/providers.tsx` con export default.
- Errores: `raise AppError(status, "mensaje")` → `{"error": {"code", "message", "details"}}`.
- Commits convencionales (`feat:`, `fix:`…), sin líneas de coautoría de IA.
