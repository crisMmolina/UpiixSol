# STATE

Phase: execution
Updated: 1795243038
AVAILABLE: UPS-068 
CLAIMED: UPS-104 
BLOCKED: UPS-057 
REVIEW: UPS-060 
INTEGRATED: (102; last 12) ... UPS-096 UPS-097 UPS-098 UPS-099 UPS-100 UPS-101 UPS-102 UPS-103 UPS-105 UPS-106 UPS-107 UPS-108 
CANCELLED: UPS-030 

Claims (first 24; status --task ID shows detail):
UPS-057 | BLOCKED | david-2 | until 1794548448 (EXPIRED: release --expired --read-summary TOKEN)
UPS-060 | REVIEW | zoe-1 | until 1795040173
UPS-104 | CLAIMED | victor-2 | until 1795257432

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1795238567 | UPS-108 | Inline detail replaces history list; tabs per status; reuse merges paso+reusar into params | Why: Keeps tab param, no new dependency
- 1795238822 | UPS-108 | Detail replaces history list inline | Why: Within Paths
- 1795238886 | UPS-103 | two files outside Paths per victor option A; merge is MERGE_HUMAN | Why: scope gate sends them to the human
- 1795241778 | UPS-107 | mix draft in reducer; list fetch ignores excludes (flip in place) | Why: no refetch on uncheck
- 1795242300 | UPS-107 | Composer.tsx and index.tsx touched, outside Paths (needed) | Why: initialState signature, export of removed AudiencePicker

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
