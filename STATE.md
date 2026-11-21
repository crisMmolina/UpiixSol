# STATE

Phase: execution
Updated: 1795238567
AVAILABLE: UPS-068 UPS-104 UPS-107 
CLAIMED: UPS-103 UPS-108 
BLOCKED: UPS-057 
REVIEW: UPS-060 
INTEGRATED: (99; last 12) ... UPS-093 UPS-094 UPS-095 UPS-096 UPS-097 UPS-098 UPS-099 UPS-100 UPS-101 UPS-102 UPS-105 UPS-106 
CANCELLED: UPS-030 

Claims (first 24; status --task ID shows detail):
UPS-057 | BLOCKED | david-2 | until 1794548448 (EXPIRED: release --expired --read-summary TOKEN)
UPS-060 | REVIEW | zoe-1 | until 1795040173
UPS-103 | CLAIMED | victor-2 | until 1795252606
UPS-108 | CLAIMED | victor-1 | until 1795252967

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1795235248 | UPS-103 | toolbar floats above block as in mock; preview keeps selection (data-keep-selection) | Why: approved UPS-102 mock
- 1795235627 | UPS-103 | raw markers while editing per plan.md; toolbar floats like mock | Why: spec/plan + approved mock
- 1795236459 | UPS-106 | Out-of-scope club 403 like GET /campaigns/{id}; order by id; CampaignDetail only on GET detail | Why: Matrix and existing test assert 403; id is stable und
- 1795236924 | deadline decision/UPS-106-1795235653/1795236553 | REVERSIBLE_AND_LOG | Option: Another club's campaign gets 403 on the delivery detail (an unknown id gets 404), the 
- 1795238567 | UPS-108 | Inline detail replaces history list; tabs per status; reuse merges paso+reusar into params | Why: Keeps tab param, no new dependency

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
