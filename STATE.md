# STATE

Phase: execution
Updated: 1794977286
AVAILABLE: UPS-068 UPS-091 UPS-094 
CLAIMED: UPS-093 
BLOCKED: UPS-057 
REVIEW: UPS-060 UPS-090 
INTEGRATED: (85; last 12) ... UPS-079 UPS-080 UPS-081 UPS-082 UPS-083 UPS-084 UPS-085 UPS-086 UPS-087 UPS-088 UPS-089 UPS-092 
CANCELLED: UPS-030 

Claims (first 24; status --task ID shows detail):
UPS-057 | BLOCKED | david-2 | until 1794548448 (EXPIRED: release --expired --read-summary TOKEN)
UPS-060 | REVIEW | zoe-1 | until 1795040173
UPS-090 | REVIEW | victor-2 | until 1795063536
UPS-093 | CLAIMED | cris-agent-1 | until 1794990539

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1794973445 | allow | victor | test change: UPS-090 | Why: victor: block composer replaces the plain body and the test send (spec 004)
- 1794973788 | UPS-088 | copy name = sha256(source key)[:32], no table; endpoint allowed for SENDERS | Why: cache without schema change; spec says academy_admin
- 1794975540 | UPS-089 | kept test_mail_template.py edit outside Paths (test send removed) | Why: its tests called /api/mail/test
- 1794975885 | deadline decision/UPS-084-1794974759/1794975659 | REVERSIBLE_AND_LOG | Option: CLAUDE.md: safe round-trip line; Why: incident guard; no money, accounts, publishing o
- 1794977136 | UPS-090 | board not pickable for club audience (server fallback) | Why: UPS-089 _sender_club

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
