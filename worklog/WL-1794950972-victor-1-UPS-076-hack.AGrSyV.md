# worklog/WL-1794950972-victor-1-UPS-076-hack.AGrSyV.md · UPS-076

## Live summary
- Done: unsubscribe POST/GET, preferences, matrix rows, docs
- Decision: body never read on POST; GET 303 to /baja
- Why: scanners prefetch GET; form/JSON/empty all work
- Failing: none
- Commands: bash .uak/bin/q uv run pytest -q --tb=short -x app/tests/test_mail_unsubscribe.py app/tests/test_mail_audience.py app/tests/test_permissions_matrix.py
- Next: Wait for review of SHA 10840dee

## History
- 1794950972 | CLAIMED | victor-1 | claim; next: stubs for the Tests names and `uak red UPS-076`; then suppressions, then the public router, then preferences.
- 1794951016 | CLAIMED | victor-1 | heartbeat; lease until 1794965416
- 1794951318 | REVIEW | victor-1 | done; PR https://github.com/crisMmolina/UpiixSol/pull/133; evidence: Verify pytest test_mail_unsubscribe+test_mail_audience+test_permissions_matrix exit 0; smoke exit 0; POST unsubscribe form/JSON, GET 303 /baja, preferences GET/PUT, matrix rows + docs regenerated · red at ec37aa8: E   AssertionError: {"error":{"code":"not_found","message":"No encontrado.","details":null}}; reviewer: -
- 1794951335 | REVIEW | victor-1 | checkpoint; next: Wait for review of SHA 10840dee
- 1794951707 | REVIEW | victor-2 | review; approve; SHA 10840deeaa3e134f122993f7cfc5d01240d61874; reviewer victor-2
