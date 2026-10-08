# worklog/WL-1791492877-joahan-claude-UPS-037-hack.i3YkbT.md · UPS-037

## Live summary
- Done: activity_events (0005), middleware capture after 2xx in BackgroundTask with own session, POST /api/analytics/events (202, 50 events, 2KB props, clamp ±5min, 30/min/user), web tracker + page.view by route template, docs/analytics.md
- Decision: -
- Why: -
- Failing: test_permissions_matrix: POST /api/analytics/events needs a MATRIX row (ANY) + regen docs/permissions-matrix.md; file outside UPS-037 Paths
- Commands: test_analytics 30 passed; full suite 423 passed 2 failed (matrix) TOTAL 100%; ruff ok; web lint no warnings in my files; build ok; e2e 12 passed; Postgres alembic up/down/up + check ok, 5 doc queries run
- Next: review

## History
- 1791492877 | CLAIMED | joahan-claude | claim; next: model + migration, then server hooks, then the client tracker and docs.
- 1791494765 | CLAIMED | joahan-claude | checkpoint; next: review
