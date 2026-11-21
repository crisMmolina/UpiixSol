# worklog/WL-1795233002-victor-1-UPS-105-hack.5fJQwE.md · UPS-105

## Live summary
- Done: Claim created; implementation pending
- Decision: Own branch and worktree
- Why: Parallel work without touching the main checkout
- Failing: No validation run yet
- Commands: `bash .uak/bin/q bash -c 'uv run pytest -q --tb=short -x app/tests/test_mail_audience_mix.py app/tests/test_mail_audience.py app/tests/test_mail_campaigns.py app/tests/test_permissions_matrix.py && DATABASE_URL=sqlite:////tmp/ups105.db uv run alembic upgrade head && DATABASE_URL=sqlite:////tmp/ups105.db uv run alembic downgrade base && npm --prefix web run build'`
- Next: after the human `uak allow`, stubs for the Tests names and `uak red UPS-105`; then the schema and `_compute`, then scope, then the migration, then the list endpoint.

## History
- 1795233002 | CLAIMED | victor-1 | claim; next: after the human `uak allow`, stubs for the Tests names and `uak red UPS-105`; then the schema and `_compute`, then scope, then the migration, then the list endpoint.
- 1795233036 | CLAIMED | victor-1 | heartbeat; lease until 1795247436
