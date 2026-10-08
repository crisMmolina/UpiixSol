# STATE

Phase: execution
Updated: 1791469608
AVAILABLE: UPS-029 
CLAIMED: -
BLOCKED: -
REVIEW: UPS-015 UPS-020 UPS-023 UPS-025 UPS-026 UPS-028 
INTEGRATED: UPS-001 UPS-002 UPS-003 UPS-004 UPS-005 UPS-006 UPS-007 UPS-008 UPS-009 UPS-010 UPS-011 UPS-012 UPS-013 UPS-014 UPS-016 
CANCELLED: -

Claims (first 24; status --task ID shows detail):
UPS-015 | REVIEW | joahan-claude | until 1791555984
UPS-020 | REVIEW | joahan-claude | until 1791555992
UPS-023 | REVIEW | joahan-2 | until 1791556008
UPS-025 | REVIEW | claude-a | until 1791530754
UPS-026 | REVIEW | joahan-3 | until 1791545528
UPS-028 | REVIEW | joahan-claude | until 1791556000

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1791441095 | UPS-022 | continue block fans out to /academies/{slug}/home for enrolled clubs; clubs grid kept on home since e2e needs Entrar a UpiixIA | Why: no global continue en
- 1791441495 | UPS-024 | stacked on feat/ups-021 (dark tokens); PR after #34 merges | Why: UPS-021 contract not on main yet
- 1791441926 | UPS-027 | No categories in API: chips = authors; trending = most recent; demo marker = demo tag + footer line (no column) | Why: No model/API changes allowed
- 1791444003 | UPS-028 | Routes, models, API paths and academy_id unchanged | Why: Task scope: only user-visible copy
- 1791445250 | deadline decision/UPS-025-1791444332/1791445232 | REVERSIBLE_AND_LOG | Option: Edit app/schemas/community.py, app/models/community.py, migration 0003, web/src/lib/ty

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
