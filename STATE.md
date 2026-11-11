# STATE

Phase: execution
Updated: 1794381433
AVAILABLE: UPS-031 UPS-040 UPS-042 UPS-044 
CLAIMED: -
BLOCKED: -
REVIEW: UPS-038 UPS-041 UPS-043 
INTEGRATED: (36; last 12) ... UPS-025 UPS-026 UPS-027 UPS-028 UPS-029 UPS-032 UPS-033 UPS-034 UPS-035 UPS-036 UPS-037 UPS-039 
CANCELLED: UPS-030 

Claims (first 24; status --task ID shows detail):
UPS-038 | REVIEW | cris-claude | until 1794458292
UPS-041 | REVIEW | cris-dev | until 1794462450
UPS-043 | REVIEW | cris-dev | until 1794467833

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1794369953 | allow | NOMBRE | test change: DSK-049 | Why: Autorizo invertir InicioV5Test:81 y exentar el campo Nombre en ScreensTourTest (quitar el texto de ejemplo)
- 1794371892 | UPS-038 | search state lifted to Player; previous lesson dims instead of skeleton | Why: audit learning.md items 1-7
- 1794374132 | deadline decision/UPS-038-1794371177/1794372077 | REVERSIBLE_AND_LOG | Option: UPS-038 adds a new file e2e/test_player.py outside its Paths; Why: acceptance asks for
- 1794376050 | UPS-041 | e2e color check retried with to_have_css | Why: getComputedStyle returns the old value until the next frame even at 0.01ms transitions
- 1794381328 | UPS-043 | dialog overflow-clip; panel exits before the backdrop; dialog closes on backdrop exit | Why: overflow-hidden dialog scrolled sideways when showModal focuse

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
