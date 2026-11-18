# worklog/WL-1794974534-victor-1-UPS-089-hack.Pq6HpW.md · UPS-089

## Live summary
- Done: Claim created; implementation pending
- Decision: Own branch and worktree
- Why: Parallel work without touching the main checkout
- Failing: No validation run yet
- Commands: `bash .uak/bin/q uv run pytest -q --tb=short -x app/tests/test_mail_campaigns.py app/tests/test_mail_preview.py app/tests/test_permissions_matrix.py`
- Next: after the human `uak allow`, stubs for the Tests names and `uak red UPS-089`; then create + preview, then send, then the removal.

## History
- 1794974534 | CLAIMED | victor-1 | claim; next: after the human `uak allow`, stubs for the Tests names and `uak red UPS-089`; then create + preview, then send, then the removal.
