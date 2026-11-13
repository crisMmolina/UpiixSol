# STATE

Phase: execution
Updated: 1794586781
AVAILABLE: UPS-068 
CLAIMED: UPS-060 
BLOCKED: UPS-057 
REVIEW: -
INTEGRATED: (64; last 12) ... UPS-054 UPS-055 UPS-056 UPS-058 UPS-059 UPS-061 UPS-062 UPS-063 UPS-064 UPS-065 UPS-067 UPS-069 
CANCELLED: UPS-030 

Claims (first 24; status --task ID shows detail):
UPS-057 | BLOCKED | david-2 | until 1794548448 (EXPIRED: release --expired --read-summary TOKEN)
UPS-060 | CLAIMED | david-3 | until 1794568206 (EXPIRED: release --expired --read-summary TOKEN)

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1794552170 | deadline lease/UPS-060/1794551315 | REQUIRES_RECOVERY | Claim kept; read the summary and use release --expired --read-summary. No work is deleted.
- 1794552492 | UPS-069 | neutral state -1, never ended | Why: Player waits for postMessage since UPS-048
- 1794552740 | UPS-067 | caplog at DEBUG | Why: e2e cannot read server output
- 1794553652 | UPS-065 | skeleton title with 2 reserved lines at every width | Why: UPS-040 no-jump rule; the title wraps on desktop too
- 1794586781 | deadline lease/UPS-060/1794568206 | REQUIRES_RECOVERY | Claim kept; read the summary and use release --expired --read-summary. No work is deleted.

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
