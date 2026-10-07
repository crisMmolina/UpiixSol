# worklog/WL-1791338036-claude-a-UPS-001-hack.sDf2Hb.md · UPS-001

## Live summary
- Done: smoke PRODUCT_PASS; pytest 33 passed 100% cov; web build 98KB gzip; real app probes ok; security-reviewer no HIGH
- Decision: Own branch and worktree
- Why: Parallel work without touching the main checkout
- Failing: No validation run yet
- Commands: `uv run ruff check app && uv run pytest -q app/tests/test_health.py && npm --prefix web run build`
- Next: Another agent reviews https://github.com/crisMmolina/UpiixSol/pull/4; run .uak/bin/smoke

## History
- 1791338036 | CLAIMED | claude-a | claim; next: follow `.uak/stacks/fastapi-react/STACK.md` §Backend setup, adding the full dependency list above in a single `uv add`.
- 1791338062 | CLAIMED | claude-a | pending decision UPS-001-1791338062; option: Install dependency set approved by @crisMmolina in chat (backend: fastapi, uvicorn[standard], sqlalchemy>=2, alembic, psycopg[binary], pydantic-settings, pydantic[email], argon2-cffi, pyjwt, slowapi, python-multipart, pillow, nh3, httpx; dev: pytest, pytest-cov, ruff, playwright; web: react-router, tailwindcss, @tailwindcss/vite, motion, @phosphor-icons/react, @fontsource/fredoka, @fontsource-variable/inter, dompurify, marked); Why: UPS-001 setup; all MIT/BSD/Apache, maintained; audit after install
- 1791338694 | REVIEW | claude-a | done; PR https://github.com/crisMmolina/UpiixSol/pull/4; evidence: smoke PRODUCT_PASS; pytest 33 passed 100% cov; web build 98KB gzip; real app probes ok; security-reviewer no HIGH; reviewer: -
