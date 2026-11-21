# worklog/WL-1795235461-victor-1-UPS-106-hack.tTnf0F.md · UPS-106

## Live summary
- Done: Claim created; implementation pending
- Decision: Own branch and worktree
- Why: Parallel work without touching the main checkout
- Failing: No validation run yet
- Commands: `bash .uak/bin/q uv run pytest -q --tb=short -x app/tests/test_mail_delivery.py app/tests/test_mail_campaigns.py app/tests/test_permissions_matrix.py`
- Next: stubs for the Tests names and `uak red UPS-106`; then the rows endpoint, then reasons, then the campaign content.

## History
- 1795235461 | CLAIMED | victor-1 | claim; next: stubs for the Tests names and `uak red UPS-106`; then the rows endpoint, then reasons, then the campaign content.
- 1795235483 | CLAIMED | victor-1 | heartbeat; lease until 1795249883
