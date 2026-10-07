# Shared-file owners

One writer per shared file. Others ask the owner with `uak msg ID --kind request`. Patterns are relative, with no spaces; directories end in `/`.
An owner is not a prerequisite for everyone: consumers work on published contracts and mocks. To transfer ownership, open a PR to main.

| Pattern | Owner task |
|---|---|
| pyproject.toml | UPS-001 |
| uv.lock | UPS-001 |
| web/package.json | UPS-001 |
| web/package-lock.json | UPS-001 |
| app/main.py | UPS-001 |
| app/config.py | UPS-001 |
| app/db.py | UPS-001 |
| app/errors.py | UPS-001 |
| app/ratelimit.py | UPS-001 |
| web/src/App.tsx | UPS-001 |
| web/vite.config.ts | UPS-001 |
| .github/workflows/ | UPS-001 |
| .gitignore | UPS-001 |
| .env.example | UPS-001 |
| app/schemas/ | UPS-002 |
| app/models/ | UPS-002 |
| app/migrations/versions/ | UPS-002 |
| app/security.py | UPS-002 |
| app/pagination.py | UPS-002 |
| app/sanitize.py | UPS-002 |
| app/services/media.py | UPS-002 |
| app/services/progress.py | UPS-002 |
| app/tests/conftest.py | UPS-002 |
| app/seed.py | UPS-002 |
| web/DESIGN.md | UPS-002 |
| web/src/lib/types.ts | UPS-002 |
| web/src/lib/ | UPS-004 |
| web/src/components/ | UPS-004 |
| web/src/layouts/ | UPS-004 |
| web/src/index.css | UPS-004 |
