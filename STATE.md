# STATE

Phase: execution
Updated: 1795233002
AVAILABLE: UPS-068 UPS-104 UPS-106 UPS-107 UPS-108 
CLAIMED: UPS-103 UPS-105 
BLOCKED: UPS-057 
REVIEW: UPS-060 
INTEGRATED: (97; last 12) ... UPS-091 UPS-092 UPS-093 UPS-094 UPS-095 UPS-096 UPS-097 UPS-098 UPS-099 UPS-100 UPS-101 UPS-102 
CANCELLED: UPS-030 

Claims (first 24; status --task ID shows detail):
UPS-057 | BLOCKED | david-2 | until 1794548448 (EXPIRED: release --expired --read-summary TOKEN)
UPS-060 | REVIEW | zoe-1 | until 1795040173
UPS-103 | CLAIMED | victor-2 | until 1795247395
UPS-105 | CLAIMED | victor-1 | until 1795247402

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1795230149 | UPS-102 | Mobile preview stays below editor (test_composer_at_390_wide relies on it); UPS-103 canvas changes it | Why: scope
- 1795230248 | UPS-102 | Screenshots referenced from .uak-shots (gitignored), sent to victor directly | Why: no image hosting for PR body
- 1795230793 | allow | victor | test change: UPS-103 | Why: victor: email canvas replaces the block form (spec 005)
- 1795231876 | UPS-101 | Plain array list per plan Contracts; superadmin manages every template; out-of-scope id 403 per spec | Why: Task criteria outrank the generic pagination ru
- 1795232819 | allow | victor | test change: UPS-105 | Why: victor: club admins see the addresses of their club (spec 006)

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
