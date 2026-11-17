# worklog/WL-1794939894-victor-2-UPS-074-hack.RazYnp.md · UPS-074

## Live summary
- Done: service+router+tests green (Verify OK), matrix rows, docs regenerated, pushed
- Decision: academy_admin individual = enrollees only (spec); outside addresses never looked up among users
- Why: spec §Audiences; avoid oracle
- Failing: full suite has ~23 failures in media/site/auth/analytics tests, checking main baseline
- Commands: bash .uak/bin/q uv run pytest -q --tb=short -x app/tests/test_mail_audience.py app/tests/test_permissions_matrix.py
- Next: review UPS-082 (#460), then baseline full suite on main, msg UPS-075 contract, /uak-ship

## History
- 1794939894 | CLAIMED | victor-2 | claim; next: stubs for the Tests names and `uak red UPS-074`; then `resolve_audience`, then the router, then the matrix rows.
- 1794939980 | CLAIMED | victor-2 | heartbeat; lease until 1794954380
- 1794941208 | CLAIMED | victor-2 | heartbeat; lease until 1794955608
- 1794941236 | CLAIMED | victor-2 | checkpoint; next: review UPS-082 (#460), then baseline full suite on main, msg UPS-075 contract, /uak-ship
