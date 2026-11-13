# STATE

Phase: execution
Updated: 1794546840
AVAILABLE: UPS-047 UPS-064 UPS-065 UPS-067 UPS-068 
CLAIMED: UPS-060 
BLOCKED: UPS-057 
REVIEW: UPS-048 UPS-055 UPS-059 UPS-062 
INTEGRATED: (55; last 12) ... UPS-045 UPS-046 UPS-049 UPS-050 UPS-051 UPS-052 UPS-053 UPS-054 UPS-056 UPS-058 UPS-061 UPS-063 
CANCELLED: UPS-030 

Claims (first 24; status --task ID shows detail):
UPS-048 | REVIEW | david-4 | until 1794633109
UPS-055 | REVIEW | david-6 | until 1794632420
UPS-057 | BLOCKED | david-2 | until 1794548448
UPS-059 | REVIEW | david-8 | until 1794629590
UPS-060 | CLAIMED | david-3 | until 1794551315
UPS-062 | REVIEW | cris-dev | until 1794632559

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1794543313 | UPS-048 | no Agent tool here: design-critic must be run by the lead; claim worktree created with git worktree add (wt new refuses owned claims) | Why: wt new check_c
- 1794545346 | deadline decision/UPS-052-1794543477/1794544377 | REVERSIBLE_AND_LOG | Option: LRN-04 is not a bug: a completed lesson stays completed; no UI or API to unmark; the e
- 1794545523 | allow | saus | test change: UPS-052 | Why: LRN-04: una clase completada no se desmarca (decisión humana 2026-11-12)
- 1794546136 | allow | crisMmolina | test change: UPS-062 | Why: unmark removed by human decision (UPS-062)
- 1794546159 | UPS-062 | drop DELETE route, completed=False branch and uncomplete_lesson; drop lesson.uncompleted event | Why: human decision: a completed lesson stays completed

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
