# STATE

Phase: execution
Updated: 1794980245
AVAILABLE: UPS-068 UPS-094 
CLAIMED: -
BLOCKED: UPS-057 
REVIEW: UPS-060 UPS-091 UPS-093 
INTEGRATED: (86; last 12) ... UPS-080 UPS-081 UPS-082 UPS-083 UPS-084 UPS-085 UPS-086 UPS-087 UPS-088 UPS-089 UPS-090 UPS-092 
CANCELLED: UPS-030 

Claims (first 24; status --task ID shows detail):
UPS-057 | BLOCKED | david-2 | until 1794548448 (EXPIRED: release --expired --read-summary TOKEN)
UPS-060 | REVIEW | zoe-1 | until 1795040173
UPS-091 | REVIEW | victor-1 | until 1795066645
UPS-093 | REVIEW | cris-agent-1 | until 1795064216

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1794977136 | UPS-090 | board not pickable for club audience (server fallback) | Why: UPS-089 _sender_club
- 1794978762 | UPS-091 | scope widened by victor | Why: needed for event/image/reply-to
- 1794978848 | deadline decision/UPS-091-1794977742/1794978642 | BLOCKED_OTHER_TASK | Option: Also edit web/src/features/mail/blocks.ts, Composer.tsx, EmailPreview.tsx (+ web/src/l
- 1794979337 | UPS-091 | done blocked by tests-only-grow on 3 e2e/test_mail.py lines | Why: spec change by design
- 1794980223 | allow | victor | test change: UPS-091 | Why: UPS-091 changes sandbox and enables Evento/Imagen

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
