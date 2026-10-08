# worklog/WL-1791492877-joahan-claude-UPS-037-hack.i3YkbT.md · UPS-037

## Live summary
- Done: review fixes: FiniteFloat props (422 not 500), properties.path reserved + free-text keys denied, subject pair required, single-INSERT server writes, keepalive flush skipRefresh, trackSearch, docs (denylist, untrusted web club ids, pool impact); matrix row moved to own section
- Decision: -
- Why: -
- Failing: -
- Commands: ruff ok; pytest 436 passed 2 skipped TOTAL 100%; web lint 0 in my files, build ok; Postgres up/down/up+check ok, non-finite repro 422 x4, suite on PG 438 passed
- Next: review

## History
- 1791492877 | CLAIMED | joahan-claude | claim; next: model + migration, then server hooks, then the client tracker and docs.
- 1791494765 | CLAIMED | joahan-claude | checkpoint; next: review
- 1791495181 | REVIEW | joahan-claude | done; PR https://github.com/crisMmolina/UpiixSol/pull/new/feat/ups-037; evidence: 73c65d4: pytest 100 %, matrix 57/57, e2e 12, PG migrations up/down/up; reviewer: -
- 1791495188 | REVIEW | joahan-claude | pending decision UPS-037-1791495188; option: UPS-037 also edits app/tests/test_permissions_matrix.py and docs/permissions-matrix.md (Paths of unclaimed UPS-036) to add its new endpoint row; Why: a new write endpoint must be in the matrix or CI fails; UPS-036 is not claimed
- 1791496368 | REVIEW | joahan-rev | review; reject; SHA 73c65d43c2d35da05b7faa84a0b4d62eb25474ba; reviewer joahan-rev
- 1791499864 | REVIEW | joahan-claude | checkpoint; next: review
- 1791500302 | REVIEW | joahan-rev | review; approve; SHA 2a08912252b41f421fb0549cbc167ffcaf819982; reviewer joahan-rev
