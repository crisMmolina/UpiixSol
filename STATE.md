# STATE

Phase: execution
Updated: 1795229525
AVAILABLE: UPS-068 UPS-101 UPS-103 UPS-104 
CLAIMED: UPS-100 UPS-102 
BLOCKED: UPS-057 
REVIEW: UPS-060 
INTEGRATED: (94; last 12) ... UPS-088 UPS-089 UPS-090 UPS-091 UPS-092 UPS-093 UPS-094 UPS-095 UPS-096 UPS-097 UPS-098 UPS-099 
CANCELLED: UPS-030 

Claims (first 24; status --task ID shows detail):
UPS-057 | BLOCKED | david-2 | until 1794548448 (EXPIRED: release --expired --read-summary TOKEN)
UPS-060 | REVIEW | zoe-1 | until 1795040173
UPS-100 | CLAIMED | victor-1 | until 1795243448
UPS-102 | CLAIMED | victor-2 | until 1795243452

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1794984457 | deadline decision/UPS-099-1794983542/1794984442 | BLOCKED_OTHER_TASK | Option: Add resvg-py (MIT) to rasterize SVG logos for email; Why: no email client shows SVG; t
- 1794985903 | UPS-095 | merged by cris over the reject of victor-3 | Why: The 1 s bound was measured on a laptop (0.3 s); on the shared GitHub runner the same code takes 1.1 s. Th
- 1794986209 | allow | victor | test change: UPS-102 | Why: victor: composer redesign in three steps (spec 005)
- 1795070186 | deadline lease/UPS-100/1795000678 | REQUIRES_RECOVERY | Claim kept; read the summary and use release --expired --read-summary. No work is deleted.
- 1795070186 | deadline lease/UPS-102/1795000687 | REQUIRES_RECOVERY | Claim kept; read the summary and use release --expired --read-summary. No work is deleted.

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
