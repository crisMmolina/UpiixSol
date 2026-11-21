# STATE

Phase: execution
Updated: 1795240111
AVAILABLE: UPS-068 UPS-104 
CLAIMED: UPS-107 
BLOCKED: UPS-057 
REVIEW: UPS-060 
INTEGRATED: (101; last 12) ... UPS-095 UPS-096 UPS-097 UPS-098 UPS-099 UPS-100 UPS-101 UPS-102 UPS-103 UPS-105 UPS-106 UPS-108 
CANCELLED: UPS-030 

Claims (first 24; status --task ID shows detail):
UPS-057 | BLOCKED | david-2 | until 1794548448 (EXPIRED: release --expired --read-summary TOKEN)
UPS-060 | REVIEW | zoe-1 | until 1795040173
UPS-107 | CLAIMED | victor-2 | until 1795254508

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1795236459 | UPS-106 | Out-of-scope club 403 like GET /campaigns/{id}; order by id; CampaignDetail only on GET detail | Why: Matrix and existing test assert 403; id is stable und
- 1795236924 | deadline decision/UPS-106-1795235653/1795236553 | REVERSIBLE_AND_LOG | Option: Another club's campaign gets 403 on the delivery detail (an unknown id gets 404), the 
- 1795238567 | UPS-108 | Inline detail replaces history list; tabs per status; reuse merges paso+reusar into params | Why: Keeps tab param, no new dependency
- 1795238822 | UPS-108 | Detail replaces history list inline | Why: Within Paths
- 1795238886 | UPS-103 | two files outside Paths per victor option A; merge is MERGE_HUMAN | Why: scope gate sends them to the human

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
