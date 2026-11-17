# worklog/WL-1794939894-victor-2-UPS-074-hack.RazYnp.md · UPS-074

## Live summary
- Done: co-admins pickable (plan PR #128) at 8bc0ad5, re-review requested
- Decision: sender excluded from own search; club-less admin picks nobody
- Why: human decision; keep pages and test assumptions stable; avoid IS NULL match
- Failing: none in Verify; worktree .env issue tracked as UPS-083
- Commands: bash .uak/bin/q uv run pytest -q --tb=short -x app/tests/test_mail_audience.py app/tests/test_permissions_matrix.py
- Next: Wait for review of SHA 8bc0ad5

## History
- 1794939894 | CLAIMED | victor-2 | claim; next: stubs for the Tests names and `uak red UPS-074`; then `resolve_audience`, then the router, then the matrix rows.
- 1794939980 | CLAIMED | victor-2 | heartbeat; lease until 1794954380
- 1794941208 | CLAIMED | victor-2 | heartbeat; lease until 1794955608
- 1794941236 | CLAIMED | victor-2 | checkpoint; next: review UPS-082 (#460), then baseline full suite on main, msg UPS-075 contract, /uak-ship
- 1794942308 | REVIEW | victor-2 | done; PR https://github.com/crisMmolina/UpiixSol/pull/127; evidence: bash .uak/bin/q uv run pytest -q --tb=short -x app/tests/test_mail_audience.py app/tests/test_permissions_matrix.py exit 0; smoke PRODUCT_PASS (741 passed) in clean checkout; new code 100% coverage; security-reviewer no HIGH, MEDIUM+LOW fixed in 188b676 · red at ec9c2d5: E   AssertionError: {"error":{"code":"not_found","message":"No encontrado.","details":null}}; reviewer: -
- 1794942360 | REVIEW | victor-2 | checkpoint; next: Wait for review of SHA 188b676
- 1794942736 | REVIEW | victor-2 | heartbeat; lease until 1795029136
- 1794942869 | REVIEW | victor-1 | review; approve; SHA 188b67679d644b5d5fb7d6c20a77427756de9592; reviewer victor-1
- 1794943226 | REVIEW | victor-2 | done; PR https://github.com/crisMmolina/UpiixSol/pull/127; evidence: bash .uak/bin/q uv run pytest -q --tb=short -x app/tests/test_mail_audience.py app/tests/test_permissions_matrix.py exit 0 at 8bc0ad5; new code 100% coverage · red at ec9c2d5: E   AssertionError: {"error":{"code":"not_found","message":"No encontrado.","details":null}}; reviewer: -
- 1794943246 | REVIEW | victor-2 | checkpoint; next: Wait for review of SHA 8bc0ad5
