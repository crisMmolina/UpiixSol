# worklog/WL-1794969567-victor-1-UPS-085-hack.xlYkAD.md · UPS-085

## Live summary
- Done: Claim created; implementation pending
- Decision: Own branch and worktree
- Why: Parallel work without touching the main checkout
- Failing: No validation run yet
- Commands: `bash .uak/bin/q bash -c 'uv run pytest -q --tb=short -x app/tests/test_mail_blocks.py app/tests/test_mailgun.py app/tests/test_mail_contract.py && DATABASE_URL=sqlite:////tmp/ups085.db uv run alembic upgrade head && DATABASE_URL=sqlite:////tmp/ups085.db uv run alembic downgrade base && npm --prefix web run build'`
- Next: stubs for the Tests names and `uak red UPS-085`; then the block models, then the migration, then the transport.

## History
- 1794969567 | CLAIMED | victor-1 | claim; next: stubs for the Tests names and `uak red UPS-085`; then the block models, then the migration, then the transport.
