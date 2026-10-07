# DECISIONS

Coordination decisions on the claims branch.
Why: a reversible option after 15 min keeps work moving.
- 1791337653 | UPS-003 | stdlib only, nocookie embed, no server fetch | Why: no key, no SSRF, works pre-setup
- 1791338714 | UPS-001 | deps installed by human (guard); TS6 no baseUrl | Why: marathon guard; TS5101
- 1791339381 | deadline decision/UPS-001-1791338062/1791338962 | REVERSIBLE_AND_LOG | Option: Install dependency set approved by @crisMmolina in chat (backend: fastapi, uvicorn[standard], sqlalchemy>=2, alembic, psycopg[binary], pydantic-settings, pydantic[email], argon2-cffi, pyjwt, slowapi, python-multipart, pillow, nh3, httpx; dev: pytest, pytest-cov, ruff, playwright; web: react-router, tailwindcss, @tailwindcss/vite, motion, @phosphor-icons/react, @fontsource/fredoka, @fontsource-variable/inter, dompurify, marked); Why: UPS-001 setup; all MIT/BSD/Apache, maintained; audit after install; no money, accounts, publishing or scope expansion.
- 1791340307 | UPS-002 | position instead of order; SVG allowlist; & stays escaped | Why: reserved word; review findings
