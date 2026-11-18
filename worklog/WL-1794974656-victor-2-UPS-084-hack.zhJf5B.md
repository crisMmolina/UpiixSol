# worklog/WL-1794974656-victor-2-UPS-084-hack.zhJf5B.md · UPS-084

## Live summary
- Done: Claim created; implementation pending
- Decision: Own branch and worktree
- Why: Parallel work without touching the main checkout
- Failing: No validation run yet
- Commands: `bash .uak/bin/q bash -c 'uv run pytest -q --tb=short -x app/tests/test_migration_guard.py && DATABASE_URL=sqlite:////tmp/ups084.db uv run alembic upgrade head && DATABASE_URL=sqlite:////tmp/ups084.db uv run alembic downgrade base'`
- Next: stubs for the Tests names and `uak red UPS-084`; then the guard in env.py.

## History
- 1794974656 | CLAIMED | victor-2 | claim; next: stubs for the Tests names and `uak red UPS-084`; then the guard in env.py.
- 1794974681 | CLAIMED | victor-2 | heartbeat; lease until 1794989081
- 1794974759 | CLAIMED | victor-2 | pending decision UPS-084-1794974759; option: CLAUDE.md: safe round-trip line; Why: incident guard
