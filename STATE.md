# STATE

Phase: execution
Updated: 1794951870
AVAILABLE: UPS-068 UPS-077 UPS-079 UPS-080 UPS-081 UPS-084 
CLAIMED: UPS-060 
BLOCKED: UPS-057 
REVIEW: UPS-076 
INTEGRATED: (73; last 12) ... UPS-065 UPS-067 UPS-069 UPS-070 UPS-071 UPS-072 UPS-073 UPS-074 UPS-075 UPS-078 UPS-082 UPS-083 
CANCELLED: UPS-030 

Claims (first 24; status --task ID shows detail):
UPS-057 | BLOCKED | david-2 | until 1794548448 (EXPIRED: release --expired --read-summary TOKEN)
UPS-060 | CLAIMED | zoe-1 | until 1794957419
UPS-076 | REVIEW | victor-1 | until 1795037735

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1794949390 | UPS-083 | conftest hook sets env_file=None on app.* BaseSettings and gives slowapi an empty config | Why: dotenv DATABASE_URL pointed to remote Postgres; global engi
- 1794950339 | deadline decision/UPS-075-1794949161/1794950061 | BLOCKED_OTHER_TASK | Option: Footer Darte de baja links to %recipient.unsubscribe_url% (API URL); UPS-076 answers G
- 1794950373 | UPS-078 | Own mail_env fixture in e2e/test_mail.py (MAIL_ENABLED, unblocked domain, seed password) | Why: conftest untouched
- 1794950614 | UPS-078 | types.ts untouched (outside Paths); History reads audience.outside locally | Why: AudienceOut.email_count in types.ts is wrong vs API
- 1794951335 | UPS-076 | body never read on POST; GET 303 to /baja | Why: scanners prefetch GET; form/JSON/empty all work

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
