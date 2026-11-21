# STATE

Phase: execution
Updated: 1795260438
AVAILABLE: UPS-068 UPS-109 
CLAIMED: UPS-104 
BLOCKED: UPS-057 
REVIEW: UPS-060 
INTEGRATED: (102; last 12) ... UPS-096 UPS-097 UPS-098 UPS-099 UPS-100 UPS-101 UPS-102 UPS-103 UPS-105 UPS-106 UPS-107 UPS-108 
CANCELLED: UPS-030 

Claims (first 24; status --task ID shows detail):
UPS-057 | BLOCKED | david-2 | until 1794548448 (EXPIRED: release --expired --read-summary TOKEN)
UPS-060 | REVIEW | zoe-1 | until 1795040173
UPS-104 | CLAIMED | victor-2 | until 1795274838

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1795241778 | UPS-107 | mix draft in reducer; list fetch ignores excludes (flip in place) | Why: no refetch on uncheck
- 1795242300 | UPS-107 | Composer.tsx and index.tsx touched, outside Paths (needed) | Why: initialState signature, export of removed AudiencePicker
- 1795243531 | allow | victor | test change: UPS-109 | Why: victor: native selects become the app menu style
- 1795243909 | UPS-104 | template origin+sig in ComposerState; Composer.tsx edited (needs Paths amend, asked human #618) | Why: save after send never blocks
- 1795244290 | UPS-104 | TemplateNameDialog mounts NameForm on open; template origin+sig in ComposerState; Composer.tsx edited (Paths amend requested, msg #618) | Why: avoid effect

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
