# worklog/WL-1794939894-victor-2-UPS-074-hack.RazYnp.md · UPS-074

## Live summary
- Done: bash .uak/bin/q uv run pytest -q --tb=short -x app/tests/test_mail_audience.py app/tests/test_permissions_matrix.py exit 0; smoke PRODUCT_PASS (741 passed) in clean checkout; new code 100% coverage; security-reviewer no HIGH, MEDIUM+LOW fixed in 188b676 · red at ec9c2d5: E   AssertionError: {"error":{"code":"not_found","message":"No encontrado.","details":null}}
- Decision: academy_admin individual = enrollees only (spec); outside addresses never looked up among users
- Why: spec §Audiences; avoid oracle
- Failing: full suite has ~23 failures in media/site/auth/analytics tests, checking main baseline
- Commands: bash .uak/bin/q uv run pytest -q --tb=short -x app/tests/test_mail_audience.py app/tests/test_permissions_matrix.py
- Next: Another agent reviews https://github.com/crisMmolina/UpiixSol/pull/127; run .uak/bin/smoke

## History
- 1794939894 | CLAIMED | victor-2 | claim; next: stubs for the Tests names and `uak red UPS-074`; then `resolve_audience`, then the router, then the matrix rows.
- 1794939980 | CLAIMED | victor-2 | heartbeat; lease until 1794954380
- 1794941208 | CLAIMED | victor-2 | heartbeat; lease until 1794955608
- 1794941236 | CLAIMED | victor-2 | checkpoint; next: review UPS-082 (#460), then baseline full suite on main, msg UPS-075 contract, /uak-ship
- 1794942308 | REVIEW | victor-2 | done; PR https://github.com/crisMmolina/UpiixSol/pull/127; evidence: bash .uak/bin/q uv run pytest -q --tb=short -x app/tests/test_mail_audience.py app/tests/test_permissions_matrix.py exit 0; smoke PRODUCT_PASS (741 passed) in clean checkout; new code 100% coverage; security-reviewer no HIGH, MEDIUM+LOW fixed in 188b676 · red at ec9c2d5: E   AssertionError: {"error":{"code":"not_found","message":"No encontrado.","details":null}}; reviewer: -
