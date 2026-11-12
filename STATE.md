# STATE

Phase: execution
Updated: 1794527791
AVAILABLE: UPS-031 UPS-047 UPS-054 UPS-055 UPS-056 UPS-057 UPS-059 UPS-060 
CLAIMED: UPS-046 
BLOCKED: -
REVIEW: UPS-048 UPS-052 
INTEGRATED: (48; last 12) ... UPS-039 UPS-040 UPS-041 UPS-042 UPS-043 UPS-044 UPS-045 UPS-049 UPS-050 UPS-051 UPS-053 UPS-058 
CANCELLED: UPS-030 

Claims (first 24; status --task ID shows detail):
UPS-046 | CLAIMED | david-claude | until 1794517644 (EXPIRED: release --expired --read-summary TOKEN)
UPS-048 | REVIEW | zoe-1 | until 1794614122
UPS-052 | REVIEW | cris-dev | until 1794549848

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1794462911 | UPS-053 | own rate-limited server for AUTH-02 | Why: shared e2e server disables the limiter
- 1794463448 | UPS-052 | QA only | Why: task
- 1794527636 | deadline lease/UPS-046/1794517644 | REQUIRES_RECOVERY | Claim kept; read the summary and use release --expired --read-summary. No work is deleted.
- 1794527636 | deadline lease/UPS-048/1794517129 | REQUIRES_RECOVERY | Claim kept; read the summary and use release --expired --read-summary. No work is deleted.
- 1794527722 | UPS-048 | clock helpers in academy-admin/clock.ts | Why: keep index.tsx parsing-free and testable

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
