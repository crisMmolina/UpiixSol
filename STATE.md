# STATE

Phase: execution
Updated: 1794542473
AVAILABLE: UPS-047 UPS-062 
CLAIMED: UPS-059 UPS-060 
BLOCKED: UPS-057 
REVIEW: UPS-048 UPS-052 UPS-055 UPS-061 UPS-063 
INTEGRATED: (52; last 12) ... UPS-042 UPS-043 UPS-044 UPS-045 UPS-046 UPS-049 UPS-050 UPS-051 UPS-053 UPS-054 UPS-056 UPS-058 
CANCELLED: UPS-030 

Claims (first 24; status --task ID shows detail):
UPS-048 | REVIEW | zoe-1 | until 1794627492
UPS-052 | REVIEW | cris-dev | until 1794549848
UPS-055 | REVIEW | zoe-1 | until 1794626789
UPS-057 | BLOCKED | david-2 | until 1794548448
UPS-059 | CLAIMED | david-8 | until 1794556176
UPS-060 | CLAIMED | david-3 | until 1794551315
UPS-061 | REVIEW | cris-dev | until 1794624674
UPS-063 | REVIEW | cris-dev | until 1794628873

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1794530899 | UPS-055 | hero_text checked instead of hero_title | Why: home renders only hero_text
- 1794535363 | UPS-046 | brief copied to docs/specs/002 (human said add it there); status sustituto instead of verificar because Verify greps bare verificar cells | Why: Verify for
- 1794535950 | UPS-056 | QA-only test file, no app changes | Why: PRUEBAS-CAMPUS §RES/EVT/ACC/BLG coverage
- 1794538274 | UPS-061 | keydown trap; skip controls in closed details via checkVisibility | Why: native showModal lets Tab leave; closed details links still report rects
- 1794541776 | deadline decision/UPS-055-1794540132/1794541032 | REVERSIBLE_AND_LOG | Option: SUP-01/ADM-03 already covered by e2e/test_flow steps 6 and 2; ADM-09 has no analytics 

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
