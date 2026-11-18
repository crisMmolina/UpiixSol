# STATE

Phase: execution
Updated: 1794974918
AVAILABLE: UPS-068 UPS-090 UPS-091 
CLAIMED: UPS-089 
BLOCKED: UPS-057 
REVIEW: UPS-060 UPS-084 
INTEGRATED: (83; last 12) ... UPS-077 UPS-078 UPS-079 UPS-080 UPS-081 UPS-082 UPS-083 UPS-085 UPS-086 UPS-087 UPS-088 UPS-092 
CANCELLED: UPS-030 

Claims (first 24; status --task ID shows detail):
UPS-057 | BLOCKED | david-2 | until 1794548448 (EXPIRED: release --expired --read-summary TOKEN)
UPS-060 | REVIEW | zoe-1 | until 1795040173
UPS-084 | REVIEW | victor-2 | until 1795061307
UPS-089 | CLAIMED | victor-1 | until 1794988965

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1794971535 | UPS-086 | inline-only HTML, no head style; sender block one pattern | Why: Gmail dark inversion + critic P1s
- 1794971700 | UPS-087 | token lookup, 404 fail-closed | Why: no leak across campaigns
- 1794973426 | allow | victor | test change: UPS-089 | Why: victor removed the test send (spec 004)
- 1794973445 | allow | victor | test change: UPS-090 | Why: victor: block composer replaces the plain body and the test send (spec 004)
- 1794973788 | UPS-088 | copy name = sha256(source key)[:32], no table; endpoint allowed for SENDERS | Why: cache without schema change; spec says academy_admin

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
