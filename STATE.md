# STATE

Phase: execution
Updated: 1795229772
AVAILABLE: UPS-068 UPS-101 UPS-103 UPS-104 
CLAIMED: UPS-102 
BLOCKED: UPS-057 
REVIEW: UPS-060 UPS-100 
INTEGRATED: (94; last 12) ... UPS-088 UPS-089 UPS-090 UPS-091 UPS-092 UPS-093 UPS-094 UPS-095 UPS-096 UPS-097 UPS-098 UPS-099 
CANCELLED: UPS-030 

Claims (first 24; status --task ID shows detail):
UPS-057 | BLOCKED | david-2 | until 1794548448 (EXPIRED: release --expired --read-summary TOKEN)
UPS-060 | REVIEW | zoe-1 | until 1795040173
UPS-100 | REVIEW | victor-1 | until 1795316172
UPS-102 | CLAIMED | victor-2 | until 1795244008

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1794986209 | allow | victor | test change: UPS-102 | Why: victor: composer redesign in three steps (spec 005)
- 1795070186 | deadline lease/UPS-100/1795000678 | REQUIRES_RECOVERY | Claim kept; read the summary and use release --expired --read-summary. No work is deleted.
- 1795070186 | deadline lease/UPS-102/1795000687 | REQUIRES_RECOVERY | Claim kept; read the summary and use release --expired --read-summary. No work is deleted.
- 1795229608 | UPS-102 | Preview in steps 2 and 3, render-only falls back to audience all | Why: UPS-100 not integrated
- 1795229772 | UPS-100 | no edits to mail_campaigns; 500 on placeholder handed to UPS-101 | Why: outside Paths

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
