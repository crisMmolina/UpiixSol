# worklog/WL-1794453591-cris-dev-UPS-044-hack.7wTUjw.md · UPS-044

## Live summary
- Done: Claim created; implementation pending
- Decision: Own branch and worktree
- Why: Parallel work without touching the main checkout
- Failing: No validation run yet
- Commands: `uv run pytest -q app/tests/test_auth.py && npm --prefix web run lint && npm --prefix web run build && uv run pytest -q e2e`
- Next: schema + service with tests, then the form and the e2e helper.

## History
- 1794453591 | CLAIMED | cris-dev | claim; next: schema + service with tests, then the form and the e2e helper.
- 1794453759 | CLAIMED | cris-dev | pending decision UPS-044-1794453759; option: Human 2026-11-12: a duplicate boleta at registration keeps the generic 409 (never says boleta vs email; test_auth.py:74-84 stays); login error becomes 'Boleta, correo o contraseña incorrectos.'; also edits web/src/features/auth/forms.tsx, validation.ts and web/src/lib/types.ts (the login form and its type live there); Why: human answered in chat; enumeration-safe registration kept; same feature folder; no money, accounts, publishing or scope expansion
