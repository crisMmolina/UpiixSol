# STATE

Phase: execution
Updated: 1794978960
AVAILABLE: UPS-068 UPS-094 
CLAIMED: UPS-091 
BLOCKED: UPS-057 
REVIEW: UPS-060 UPS-093 
INTEGRATED: (86; last 12) ... UPS-080 UPS-081 UPS-082 UPS-083 UPS-084 UPS-085 UPS-086 UPS-087 UPS-088 UPS-089 UPS-090 UPS-092 
CANCELLED: UPS-030 

Claims (first 24; status --task ID shows detail):
UPS-057 | BLOCKED | david-2 | until 1794548448 (EXPIRED: release --expired --read-summary TOKEN)
UPS-060 | REVIEW | zoe-1 | until 1795040173
UPS-091 | CLAIMED | victor-1 | until 1794993319
UPS-093 | REVIEW | cris-agent-1 | until 1795064216

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1794975540 | UPS-089 | kept test_mail_template.py edit outside Paths (test send removed) | Why: its tests called /api/mail/test
- 1794975885 | deadline decision/UPS-084-1794974759/1794975659 | REVERSIBLE_AND_LOG | Option: CLAUDE.md: safe round-trip line; Why: incident guard; no money, accounts, publishing o
- 1794977136 | UPS-090 | board not pickable for club audience (server fallback) | Why: UPS-089 _sender_club
- 1794978762 | UPS-091 | scope widened by victor | Why: needed for event/image/reply-to
- 1794978848 | deadline decision/UPS-091-1794977742/1794978642 | BLOCKED_OTHER_TASK | Option: Also edit web/src/features/mail/blocks.ts, Composer.tsx, EmailPreview.tsx (+ web/src/l

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
