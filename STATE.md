# STATE

Phase: execution
Updated: 1794949650
AVAILABLE: UPS-068 UPS-076 UPS-077 UPS-078 UPS-079 UPS-080 UPS-081 UPS-084 
CLAIMED: UPS-060 
BLOCKED: UPS-057 
REVIEW: UPS-075 UPS-083 
INTEGRATED: (70; last 12) ... UPS-062 UPS-063 UPS-064 UPS-065 UPS-067 UPS-069 UPS-070 UPS-071 UPS-072 UPS-073 UPS-074 UPS-082 
CANCELLED: UPS-030 

Claims (first 24; status --task ID shows detail):
UPS-057 | BLOCKED | david-2 | until 1794548448 (EXPIRED: release --expired --read-summary TOKEN)
UPS-060 | CLAIMED | zoe-1 | until 1794957419
UPS-075 | REVIEW | victor-2 | until 1795035743
UPS-083 | REVIEW | victor-1 | until 1795035790

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1794942360 | UPS-074 | non-superadmin preview blind to typed-address dedup/suppression; individual = enrollees only | Why: security review oracle findings; spec §Audiences
- 1794943006 | UPS-073 | marathon: human CODEOWNERS merge | Why: mode rule
- 1794943246 | UPS-074 | sender excluded from own search; club-less admin picks nobody | Why: human decision; keep pages and test assumptions stable; avoid IS NULL match
- 1794949343 | UPS-075 | Footer links %recipient.unsubscribe_url%; UPS-076 should 303 GET to /baja | Why: Mailgun only gets name and unsubscribe_url variables
- 1794949390 | UPS-083 | conftest hook sets env_file=None on app.* BaseSettings and gives slowapi an empty config | Why: dotenv DATABASE_URL pointed to remote Postgres; global engi

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
