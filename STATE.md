# STATE

Phase: execution
Updated: 1794536760
AVAILABLE: UPS-047 UPS-059 
CLAIMED: UPS-060 
BLOCKED: UPS-057 
REVIEW: UPS-031 UPS-046 UPS-048 UPS-052 UPS-054 UPS-055 UPS-056 
INTEGRATED: (48; last 12) ... UPS-039 UPS-040 UPS-041 UPS-042 UPS-043 UPS-044 UPS-045 UPS-049 UPS-050 UPS-051 UPS-053 UPS-058 
CANCELLED: UPS-030 

Claims (first 24; status --task ID shows detail):
UPS-031 | REVIEW | david-1 | until 1794622486
UPS-046 | REVIEW | david-claude | until 1794622566
UPS-048 | REVIEW | zoe-1 | until 1794614122
UPS-052 | REVIEW | cris-dev | until 1794549848
UPS-054 | REVIEW | zoe-1 | until 1794616033
UPS-055 | REVIEW | zoe-1 | until 1794617299
UPS-056 | REVIEW | zoe-1 | until 1794622350
UPS-057 | BLOCKED | david-2 | until 1794548448
UPS-060 | CLAIMED | david-3 | until 1794547667

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1794527722 | UPS-048 | clock helpers in academy-admin/clock.ts | Why: keep index.tsx parsing-free and testable
- 1794529633 | UPS-054 | superadmin moderates General in e2e | Why: General has no academy
- 1794530899 | UPS-055 | hero_text checked instead of hero_title | Why: home renders only hero_text
- 1794535363 | UPS-046 | brief copied to docs/specs/002 (human said add it there); status sustituto instead of verificar because Verify greps bare verificar cells | Why: Verify for
- 1794535950 | UPS-056 | QA-only test file, no app changes | Why: PRUEBAS-CAMPUS §RES/EVT/ACC/BLG coverage

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
