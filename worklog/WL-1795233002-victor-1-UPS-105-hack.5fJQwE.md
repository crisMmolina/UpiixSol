# worklog/WL-1795233002-victor-1-UPS-105-hack.5fJQwE.md · UPS-105

## Live summary
- Done: PR #168 at 9e3cd5e, REVIEW
- Decision: removed mix-only; create stays non-blind (debt)
- Why: old kinds unchanged; blind drafts out of scope
- Failing: none
- Commands: Verify from TASKS.md
- Next: Wait for review of SHA 9e3cd5e

## History
- 1795233002 | CLAIMED | victor-1 | claim; next: after the human `uak allow`, stubs for the Tests names and `uak red UPS-105`; then the schema and `_compute`, then scope, then the migration, then the list endpoint.
- 1795233036 | CLAIMED | victor-1 | heartbeat; lease until 1795247436
- 1795233866 | CLAIMED | victor-1 | checkpoint; next: /uak-ship: contract msg, push, PR, security-reviewer, uak done
- 1795234253 | CLAIMED | victor-1 | heartbeat; lease until 1795248653
- 1795234276 | CLAIMED | victor-1 | pending decision UPS-105-1795234276; option: Keep create non-blind (pre-existing draft oracle on typed addresses, now also via mix) and no rate limit on audience/list; flag both to victor as debt; Why: fixing needs blind drafts filtered at send time (changes create/send contract and existing tests, beyond UPS-105); preview has no limit either
- 1795234295 | REVIEW | victor-1 | done; PR https://github.com/crisMmolina/UpiixSol/pull/168; evidence: Verify exit 0 at 9e3cd5e; smoke exit 0; full pytest green 99% cov; security-reviewer no HIGH (MEDIUM pre-existing draft oracle + LOW rate limit recorded as decision) · existing tests changed with a human's approval (victor) · red at ae798a1: FAILED app/tests/test_mail_audience_mix.py::test_mail_audience_mix_migration_round_trips_on_sqlite · existing tests changed with a human's approval (victor) · red at ae798a1: FAILED app/tests/test_mail_audience_mix.py::test_mail_audience_mix_migration_round_trips_on_sqlite; reviewer: -
- 1795234303 | REVIEW | victor-1 | checkpoint; next: Wait for review of SHA 9e3cd5e
- 1795234967 | REVIEW | victor-3 | review; approve; SHA 9e3cd5e52f2f7915b3f5b29e0d4807cccbb16d6c; reviewer victor-3
