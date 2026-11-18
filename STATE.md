# STATE

Phase: execution
Updated: 1794982406
AVAILABLE: UPS-068 UPS-095 
CLAIMED: UPS-097 
BLOCKED: UPS-057 
REVIEW: UPS-060 UPS-094 UPS-096 
INTEGRATED: (88; last 12) ... UPS-082 UPS-083 UPS-084 UPS-085 UPS-086 UPS-087 UPS-088 UPS-089 UPS-090 UPS-091 UPS-092 UPS-093 
CANCELLED: UPS-030 

Claims (first 24; status --task ID shows detail):
UPS-057 | BLOCKED | david-2 | until 1794548448 (EXPIRED: release --expired --read-summary TOKEN)
UPS-060 | REVIEW | zoe-1 | until 1795040173
UPS-094 | REVIEW | cris-agent-1 | until 1795067666
UPS-096 | REVIEW | victor-1 | until 1795068719
UPS-097 | CLAIMED | victor-2 | until 1794996327

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1794980223 | allow | victor | test change: UPS-091 | Why: UPS-091 changes sandbox and enables Evento/Imagen
- 1794981266 | UPS-094 | Edit mode added to event form so replace/remove work; photo failure on create turns the form into an edit of the new event | Why: Retry must not duplicate 
- 1794981508 | allow | victor | test change: UPS-096 | Why: victor verified the per-recipient List-Unsubscribe in a batch
- 1794981783 | allow | victor | test change: UPS-097 | Why: victor: no per-campaign cap on outside addresses, monthly quota only
- 1794982319 | UPS-096 | always batch with %recipient.unsubscribe_url% | Why: victor verified 2026-11-18

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
