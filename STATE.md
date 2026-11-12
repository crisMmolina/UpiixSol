# STATE

Phase: execution
Updated: 1794461928
AVAILABLE: UPS-031 UPS-048 UPS-047 UPS-052 UPS-053 UPS-054 UPS-055 UPS-056 UPS-057 UPS-058 UPS-059 UPS-060 UPS-046 
CLAIMED: UPS-051 
BLOCKED: -
REVIEW: UPS-040 UPS-045 
INTEGRATED: (43; last 12) ... UPS-034 UPS-035 UPS-036 UPS-037 UPS-038 UPS-039 UPS-041 UPS-042 UPS-043 UPS-044 UPS-049 UPS-050 
CANCELLED: UPS-030 

Claims (first 24; status --task ID shows detail):
UPS-040 | REVIEW | cris-dev | until 1794547171
UPS-045 | REVIEW | cris-dev | until 1794543119
UPS-051 | CLAIMED | cris-dev | until 1794475950

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1794455376 | allow | NAME | test change: UPS-044 | Why: login es Boleta o correo (UPS-044)
- 1794455398 | UPS-044 | human allowed the 4 edited assertions | Why: the login spec changed (Boleta o correo)
- 1794456719 | UPS-045 | playerSrc fix pulled in from UPS-048 Paths | Why: UPS-045 alone would break embeds of lessons saved with ?t=
- 1794458486 | deadline decision/UPS-045-1794456491/1794457391 | REVERSIBLE_AND_LOG | Option: UPS-045 also changes playerSrc() in web/src/features/learning/youtube.ts (in UPS-048 P
- 1794460771 | UPS-040 | heroes render real static parts while loading; reserved text heights; logo min width | Why: skeleton→content shifts up to 226px at 390

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
