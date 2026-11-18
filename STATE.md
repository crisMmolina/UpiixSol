# STATE

Phase: execution
Updated: 1794971535
AVAILABLE: UPS-068 UPS-084 UPS-088 UPS-089 UPS-090 UPS-091 UPS-092 
CLAIMED: UPS-087 
BLOCKED: UPS-057 
REVIEW: UPS-060 UPS-086 
INTEGRATED: (79; last 12) ... UPS-073 UPS-074 UPS-075 UPS-076 UPS-077 UPS-078 UPS-079 UPS-080 UPS-081 UPS-082 UPS-083 UPS-085 
CANCELLED: UPS-030 

Claims (first 24; status --task ID shows detail):
UPS-057 | BLOCKED | david-2 | until 1794548448 (EXPIRED: release --expired --read-summary TOKEN)
UPS-060 | REVIEW | zoe-1 | until 1795040173
UPS-086 | REVIEW | victor-1 | until 1795057935
UPS-087 | CLAIMED | victor-2 | until 1794985441

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1794954588 | UPS-081 | finished_at cutoff; snapshot only when rows exist | Why: second run must not zero the snapshot
- 1794954598 | UPS-080 | MAIL_ENABLED and MAILGUN_TEST_MODE sync:false so redeploys never override the dashboard or rollback | Why: blueprint value would overwrite manual flips
- 1794970108 | UPS-085 | batch_alter_table for SQLite FK/unique; MX tz fixed UTC-6 | Why: SQLite cannot ALTER constraints
- 1794971067 | allow | victor | test change: UPS-092 | Why: victor: monthly Mailgun quota replaces the daily placeholder
- 1794971535 | UPS-086 | inline-only HTML, no head style; sender block one pattern | Why: Gmail dark inversion + critic P1s

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
