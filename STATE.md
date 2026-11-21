# STATE

Phase: execution
Updated: 1795234295
AVAILABLE: UPS-068 UPS-104 UPS-106 UPS-107 UPS-108 
CLAIMED: UPS-103 
BLOCKED: UPS-057 
REVIEW: UPS-060 UPS-105 
INTEGRATED: (97; last 12) ... UPS-091 UPS-092 UPS-093 UPS-094 UPS-095 UPS-096 UPS-097 UPS-098 UPS-099 UPS-100 UPS-101 UPS-102 
CANCELLED: UPS-030 

Claims (first 24; status --task ID shows detail):
UPS-057 | BLOCKED | david-2 | until 1794548448 (EXPIRED: release --expired --read-summary TOKEN)
UPS-060 | REVIEW | zoe-1 | until 1795040173
UPS-103 | CLAIMED | victor-2 | until 1795248690
UPS-105 | REVIEW | victor-1 | until 1795320695

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1795231876 | UPS-101 | Plain array list per plan Contracts; superadmin manages every template; out-of-scope id 403 per spec | Why: Task criteria outrank the generic pagination ru
- 1795232819 | allow | victor | test change: UPS-105 | Why: victor: club admins see the addresses of their club (spec 006)
- 1795233283 | allow | victor | test change: UPS-107 | Why: victor: combined recipients list replaces the one-kind picker (spec 006)
- 1795233837 | UPS-103 | CanvasMock kept (index.tsx out of Paths); preview behind 'Ver como llega' native dialog; textarea always mounted under aria-hidden formatted view | Why: Pa
- 1795233866 | UPS-105 | removed is mix-only in preview; origins are codes all|academy:<id>|role:<r>|picked|outside | Why: old kinds unchanged (exact-dict test); web maps labels

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
