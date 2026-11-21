# worklog/WL-1795230569-victor-1-UPS-101-hack.JlZs8G.md · UPS-101

## Live summary
- Done: Claim created; implementation pending
- Decision: Own branch and worktree
- Why: Parallel work without touching the main checkout
- Failing: No validation run yet
- Commands: `bash .uak/bin/q uv run pytest -q --tb=short -x app/tests/test_mail_templates.py app/tests/test_mail_preview.py app/tests/test_permissions_matrix.py`
- Next: stubs for the Tests names and `uak red UPS-101`; then list, then save, then rename/delete, then the preview theme.

## History
- 1795230569 | CLAIMED | victor-1 | claim; next: stubs for the Tests names and `uak red UPS-101`; then list, then save, then rename/delete, then the preview theme.
