# STATE

Phase: execution
Updated: 1794381457
AVAILABLE: UPS-031 UPS-040 UPS-044 
CLAIMED: UPS-042 
BLOCKED: -
REVIEW: UPS-038 UPS-041 UPS-043 
INTEGRATED: (36; last 12) ... UPS-025 UPS-026 UPS-027 UPS-028 UPS-029 UPS-032 UPS-033 UPS-034 UPS-035 UPS-036 UPS-037 UPS-039 
CANCELLED: UPS-030 

Claims (first 24; status --task ID shows detail):
UPS-038 | REVIEW | cris-claude | until 1794458292
UPS-041 | REVIEW | cris-dev | until 1794462450
UPS-042 | CLAIMED | cris-dev | until 1794395857
UPS-043 | REVIEW | cris-dev | until 1794467851

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1794371892 | UPS-038 | search state lifted to Player; previous lesson dims instead of skeleton | Why: audit learning.md items 1-7
- 1794374132 | deadline decision/UPS-038-1794371177/1794372077 | REVERSIBLE_AND_LOG | Option: UPS-038 adds a new file e2e/test_player.py outside its Paths; Why: acceptance asks for
- 1794376050 | UPS-041 | e2e color check retried with to_have_css | Why: getComputedStyle returns the old value until the next frame even at 0.01ms transitions
- 1794381328 | UPS-043 | dialog overflow-clip; panel exits before the backdrop; dialog closes on backdrop exit | Why: overflow-hidden dialog scrolled sideways when showModal focuse
- 1794381451 | UPS-043 | dialog overflow-clip; panel exits before backdrop; close on backdrop exit | Why: overflow-hidden dialog scrolled sideways on showModal focus (scrollLeft 34

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
