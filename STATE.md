# STATE

Phase: execution
Updated: 1794439736
AVAILABLE: UPS-031 UPS-040 UPS-044 UPS-045 UPS-046 UPS-048 UPS-047 
CLAIMED: -
BLOCKED: -
REVIEW: UPS-038 UPS-041 UPS-042 UPS-043 
INTEGRATED: (36; last 12) ... UPS-025 UPS-026 UPS-027 UPS-028 UPS-029 UPS-032 UPS-033 UPS-034 UPS-035 UPS-036 UPS-037 UPS-039 
CANCELLED: UPS-030 

Claims (first 24; status --task ID shows detail):
UPS-038 | REVIEW | cris-claude | until 1794458292
UPS-041 | REVIEW | cris-dev | until 1794462450
UPS-042 | REVIEW | cris-dev | until 1794468568
UPS-043 | REVIEW | cris-dev | until 1794467851

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1794376050 | UPS-041 | e2e color check retried with to_have_css | Why: getComputedStyle returns the old value until the next frame even at 0.01ms transitions
- 1794381328 | UPS-043 | dialog overflow-clip; panel exits before the backdrop; dialog closes on backdrop exit | Why: overflow-hidden dialog scrolled sideways when showModal focuse
- 1794381451 | UPS-043 | dialog overflow-clip; panel exits before backdrop; close on backdrop exit | Why: overflow-hidden dialog scrolled sideways on showModal focus (scrollLeft 34
- 1794382168 | UPS-042 | top padding computed once with the mount-time block height; resize recenters with it | Why: flex centering would move the card top on tab/message changes; 
- 1794436396 | deadline decision/UPS-042-1794382115/1794383015 | REVERSIBLE_AND_LOG | Option: UPS-042 edits one rule in web/DESIGN.md (owned by integrated UPS-039): the login is ce

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
