# STATE

Phase: execution
Updated: 1795296721
AVAILABLE: UPS-068 
CLAIMED: -
BLOCKED: UPS-057 
REVIEW: UPS-060 
INTEGRATED: (104; last 12) ... UPS-098 UPS-099 UPS-100 UPS-101 UPS-102 UPS-103 UPS-104 UPS-105 UPS-106 UPS-107 UPS-108 UPS-109 
CANCELLED: UPS-030 

Claims (first 24; status --task ID shows detail):
UPS-057 | BLOCKED | david-2 | until 1794548448 (EXPIRED: release --expired --read-summary TOKEN)
UPS-060 | REVIEW | zoe-1 | until 1795040173

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1795243531 | allow | victor | test change: UPS-109 | Why: victor: native selects become the app menu style
- 1795243909 | UPS-104 | template origin+sig in ComposerState; Composer.tsx edited (needs Paths amend, asked human #618) | Why: save after send never blocks
- 1795244290 | UPS-104 | TemplateNameDialog mounts NameForm on open; template origin+sig in ComposerState; Composer.tsx edited (Paths amend requested, msg #618) | Why: avoid effect
- 1795282140 | UPS-104 | Composer.tsx edited outside Paths: merge gate sends it to the human | Why: save on send and template load hook into its confirm()
- 1795295930 | UPS-109 | viewport shots 1280/390; check uses text-secondary | Why: AA for the check, bottom bar never covers the list

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
