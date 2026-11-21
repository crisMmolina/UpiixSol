# worklog/WL-1795233002-victor-1-UPS-105-hack.5fJQwE.md · UPS-105

## Live summary
- Done: mix schema, _resolve, list endpoint, scope, migration 0012, visibility, web labels; Verify green at 667b56b
- Decision: removed is mix-only in preview; origins are codes all|academy:<id>|role:<r>|picked|outside
- Why: old kinds unchanged (exact-dict test); web maps labels
- Failing: none
- Commands: Verify from TASKS.md
- Next: /uak-ship: contract msg, push, PR, security-reviewer, uak done

## History
- 1795233002 | CLAIMED | victor-1 | claim; next: after the human `uak allow`, stubs for the Tests names and `uak red UPS-105`; then the schema and `_compute`, then scope, then the migration, then the list endpoint.
- 1795233036 | CLAIMED | victor-1 | heartbeat; lease until 1795247436
- 1795233866 | CLAIMED | victor-1 | checkpoint; next: /uak-ship: contract msg, push, PR, security-reviewer, uak done
- 1795234253 | CLAIMED | victor-1 | heartbeat; lease until 1795248653
- 1795234276 | CLAIMED | victor-1 | pending decision UPS-105-1795234276; option: Keep create non-blind (pre-existing draft oracle on typed addresses, now also via mix) and no rate limit on audience/list; flag both to victor as debt; Why: fixing needs blind drafts filtered at send time (changes create/send contract and existing tests, beyond UPS-105); preview has no limit either
