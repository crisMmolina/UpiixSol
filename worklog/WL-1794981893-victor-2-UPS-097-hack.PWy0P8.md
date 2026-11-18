# worklog/WL-1794981893-victor-2-UPS-097-hack.PWy0P8.md · UPS-097

## Live summary
- Done: Claim created; implementation pending
- Decision: Own branch and worktree
- Why: Parallel work without touching the main checkout
- Failing: No validation run yet
- Commands: `bash .uak/bin/q bash -c 'uv run pytest -q --tb=short -x app/tests/test_mail_audience.py && npm --prefix web run lint && npm --prefix web run build && uv run pytest -q e2e/test_mail_paste.py'`
- Next: after the human `uak allow`, stubs for the Tests names and `uak red UPS-097`; then the API cap, then the paste parser, then the UI.

## History
- 1794981893 | CLAIMED | victor-2 | claim; next: after the human `uak allow`, stubs for the Tests names and `uak red UPS-097`; then the API cap, then the paste parser, then the UI.
- 1794981927 | CLAIMED | victor-2 | heartbeat; lease until 1794996327
