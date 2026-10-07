# worklog/WL-1791338036-claude-a-UPS-001-hack.sDf2Hb.md · UPS-001

## Live summary
- Done: smoke PRODUCT_PASS; pytest 33 passed 100% cov; web build 98KB gzip; real app probes ok; security-reviewer no HIGH; uak gates toolchain fixed in 2dc493e
- Decision: deps installed by human (guard); TS6 no baseUrl
- Why: marathon guard; TS5101
- Failing: none
- Commands: bash .uak/bin/smoke
- Next: Another agent reviews https://github.com/crisMmolina/UpiixSol/pull/4; run .uak/bin/smoke

## History
- 1791338036 | CLAIMED | claude-a | claim; next: follow `.uak/stacks/fastapi-react/STACK.md` §Backend setup, adding the full dependency list above in a single `uv add`.
- 1791338062 | CLAIMED | claude-a | pending decision UPS-001-1791338062; option: Install dependency set approved by @crisMmolina in chat (backend: fastapi, uvicorn[standard], sqlalchemy>=2, alembic, psycopg[binary], pydantic-settings, pydantic[email], argon2-cffi, pyjwt, slowapi, python-multipart, pillow, nh3, httpx; dev: pytest, pytest-cov, ruff, playwright; web: react-router, tailwindcss, @tailwindcss/vite, motion, @phosphor-icons/react, @fontsource/fredoka, @fontsource-variable/inter, dompurify, marked); Why: UPS-001 setup; all MIT/BSD/Apache, maintained; audit after install
- 1791338694 | REVIEW | claude-a | done; PR https://github.com/crisMmolina/UpiixSol/pull/4; evidence: smoke PRODUCT_PASS; pytest 33 passed 100% cov; web build 98KB gzip; real app probes ok; security-reviewer no HIGH; reviewer: -
- 1791338714 | REVIEW | claude-a | checkpoint; next: Wait for review of SHA 54ac53b
- 1791338741 | REVIEW | claude-a | done; PR https://github.com/crisMmolina/UpiixSol/pull/4; evidence: smoke PRODUCT_PASS; pytest 33 passed 100% cov; web build 98KB gzip; real app probes ok; security-reviewer no HIGH; uak gates toolchain fixed in 2dc493e; reviewer: -
