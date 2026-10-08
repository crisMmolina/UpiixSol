# Shared-file owners

One writer per shared file. Others ask the owner with `uak msg ID --kind request`. Patterns are relative, with no spaces; directories end in `/`.
An owner is not a prerequisite for everyone: consumers work on published contracts and mocks. To transfer ownership, open a PR to main.

| Pattern | Owner task |
|---|---|
| pyproject.toml | UPS-001 |
| uv.lock | UPS-001 |
| web/package.json | UPS-001 |
| web/package-lock.json | UPS-001 |
| app/main.py | UPS-037 |
| app/config.py | UPS-020 |
| app/db.py | UPS-001 |
| app/errors.py | UPS-001 |
| app/ratelimit.py | UPS-020 |
| alembic.ini | UPS-001 |
| app/migrations/env.py | UPS-001 |
| app/migrations/script.py.mako | UPS-001 |
| web/src/App.tsx | UPS-037 |
| web/vite.config.ts | UPS-001 |
| .github/workflows/ | UPS-001 |
| .gitignore | UPS-001 |
| .env.example | UPS-020 |
| app/schemas/ | UPS-002 |
| app/models/__init__.py | UPS-037 |
| app/models/academy.py | UPS-002 |
| app/models/common.py | UPS-002 |
| app/models/community.py | UPS-002 |
| app/models/content.py | UPS-002 |
| app/models/learning.py | UPS-002 |
| app/models/user.py | UPS-020 |
| app/migrations/versions/0001_initial.py | UPS-002 |
| app/migrations/versions/0002_password_changed_at.py | UPS-020 |
| app/migrations/versions/0004_media_objects.py | UPS-030 |
| app/migrations/versions/0005_activity_events.py | UPS-037 |
| app/security.py | UPS-020 |
| app/pagination.py | UPS-002 |
| app/sanitize.py | UPS-002 |
| app/services/media.py | UPS-035 |
| app/services/progress.py | UPS-002 |
| app/tests/conftest.py | UPS-020 |
| app/seed.py | UPS-031 |
| web/DESIGN.md | UPS-033 |
| web/src/lib/types.ts | UPS-002 |
| web/src/lib/api.ts | UPS-020 |
| web/src/lib/auth.tsx | UPS-033 |
| web/src/lib/theme.tsx | UPS-032 |
| web/src/lib/providers.tsx | UPS-021 |
| web/src/components/ | UPS-033 |
| web/src/layouts/ | UPS-032 |
| web/src/index.css | UPS-032 |
| app/fixtures/demo.json | UPS-027 |
