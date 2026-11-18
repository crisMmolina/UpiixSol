# STATE

Phase: execution
Updated: 1794985266
AVAILABLE: UPS-068 
CLAIMED: -
BLOCKED: UPS-057 
REVIEW: UPS-060 UPS-095 UPS-099 
INTEGRATED: (92; last 12) ... UPS-086 UPS-087 UPS-088 UPS-089 UPS-090 UPS-091 UPS-092 UPS-093 UPS-094 UPS-096 UPS-097 UPS-098 
CANCELLED: UPS-030 

Claims (first 24; status --task ID shows detail):
UPS-057 | BLOCKED | david-2 | until 1794548448 (EXPIRED: release --expired --read-summary TOKEN)
UPS-060 | REVIEW | zoe-1 | until 1795040173
UPS-095 | REVIEW | cris-agent-1 | until 1795070517
UPS-099 | REVIEW | victor-1 | until 1795071554

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1794982319 | UPS-096 | always batch with %recipient.unsubscribe_url% | Why: victor verified 2026-11-18
- 1794982868 | UPS-097 | quota check in preview only | Why: campaign create must succeed, send rejects
- 1794984117 | UPS-095 | notice computed client-side; X-Background-Removed header for API clients | Why: api.ts is outside Paths
- 1794984225 | allow | victor | test change: UPS-099 | Why: victor: SVG logos now get a PNG email copy
- 1794984457 | deadline decision/UPS-099-1794983542/1794984442 | BLOCKED_OTHER_TASK | Option: Add resvg-py (MIT) to rasterize SVG logos for email; Why: no email client shows SVG; t

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
