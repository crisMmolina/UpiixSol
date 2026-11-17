# worklog/WL-1794943871-victor-2-UPS-075-hack.m1W2sA.md · UPS-075

## Live summary
- Done: Claim created; implementation pending
- Decision: Own branch and worktree
- Why: Parallel work without touching the main checkout
- Failing: No validation run yet
- Commands: `bash .uak/bin/q uv run pytest -q --tb=short -x app/tests/test_mail_template.py app/tests/test_mail_campaigns.py app/tests/test_permissions_matrix.py`
- Next: stubs for the Tests names and `uak red UPS-075`; then the template, then draft and confirm, then background sending.

## History
- 1794943871 | CLAIMED | victor-2 | claim; next: stubs for the Tests names and `uak red UPS-075`; then the template, then draft and confirm, then background sending.
