# STATE

Phase: execution
Updated: 1794463330
AVAILABLE: UPS-031 UPS-048 UPS-047 UPS-054 UPS-055 UPS-056 UPS-057 UPS-059 UPS-060 UPS-046 
CLAIMED: UPS-052 
BLOCKED: -
REVIEW: UPS-040 UPS-045 UPS-051 UPS-053 UPS-058 
INTEGRATED: (43; last 12) ... UPS-034 UPS-035 UPS-036 UPS-037 UPS-038 UPS-039 UPS-041 UPS-042 UPS-043 UPS-044 UPS-049 UPS-050 
CANCELLED: UPS-030 

Claims (first 24; status --task ID shows detail):
UPS-040 | REVIEW | cris-dev | until 1794547171
UPS-045 | REVIEW | cris-dev | until 1794543119
UPS-051 | REVIEW | cris-dev | until 1794548462
UPS-052 | CLAIMED | cris-dev | until 1794477325
UPS-053 | REVIEW | cris-dev | until 1794549311
UPS-058 | REVIEW | cris-dev | until 1794548801

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1794458486 | deadline decision/UPS-045-1794456491/1794457391 | REVERSIBLE_AND_LOG | Option: UPS-045 also changes playerSrc() in web/src/features/learning/youtube.ts (in UPS-048 P
- 1794460771 | UPS-040 | heroes render real static parts while loading; reserved text heights; logo min width | Why: skeleton→content shifts up to 226px at 390
- 1794462062 | UPS-051 | reuse matrix fixtures; QA only, no fixes | Why: task: mismatches become new tasks
- 1794462401 | UPS-058 | QA only | Why: task
- 1794462911 | UPS-053 | own rate-limited server for AUTH-02 | Why: shared e2e server disables the limiter

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
