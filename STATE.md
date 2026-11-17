# STATE

Phase: execution
Updated: 1794954576
AVAILABLE: UPS-068 UPS-084 
CLAIMED: UPS-080 
BLOCKED: UPS-057 
REVIEW: UPS-060 UPS-081 
INTEGRATED: (76; last 12) ... UPS-070 UPS-071 UPS-072 UPS-073 UPS-074 UPS-075 UPS-076 UPS-077 UPS-078 UPS-079 UPS-082 UPS-083 
CANCELLED: UPS-030 

Claims (first 24; status --task ID shows detail):
UPS-057 | BLOCKED | david-2 | until 1794548448 (EXPIRED: release --expired --read-summary TOKEN)
UPS-060 | REVIEW | zoe-1 | until 1795040173
UPS-080 | CLAIMED | victor-1 | until 1794968788
UPS-081 | REVIEW | victor-2 | until 1795040976

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1794950614 | UPS-078 | types.ts untouched (outside Paths); History reads audience.outside locally | Why: AudienceOut.email_count in types.ts is wrong vs API
- 1794951335 | UPS-076 | body never read on POST; GET 303 to /baja | Why: scanners prefetch GET; form/JSON/empty all work
- 1794952352 | UPS-077 | suppress by address even if campaign unknown; mail_suppressions.py untouched (own _suppress) | Why: complained fixture has no campaign_id; stay inside Path
- 1794952588 | UPS-079 | ownClub prop on picker/composer/history | Why: reuse UPS-078 pieces
- 1794953773 | UPS-060 | Verify exit 1 reported as the real breaking point, not hidden | Why: criteria: numbers only from real runs; 20 users exceeds p95 1500 ms

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
