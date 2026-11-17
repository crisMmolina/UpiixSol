# STATE

Phase: execution
Updated: 1794949343
AVAILABLE: UPS-068 UPS-076 UPS-077 UPS-078 UPS-079 UPS-080 UPS-081 
CLAIMED: UPS-060 UPS-083 
BLOCKED: UPS-057 
REVIEW: UPS-075 
INTEGRATED: (70; last 12) ... UPS-062 UPS-063 UPS-064 UPS-065 UPS-067 UPS-069 UPS-070 UPS-071 UPS-072 UPS-073 UPS-074 UPS-082 
CANCELLED: UPS-030 

Claims (first 24; status --task ID shows detail):
UPS-057 | BLOCKED | david-2 | until 1794548448 (EXPIRED: release --expired --read-summary TOKEN)
UPS-060 | CLAIMED | zoe-1 | until 1794957419
UPS-075 | REVIEW | victor-2 | until 1795035743
UPS-083 | CLAIMED | victor-1 | until 1794963421

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1794942252 | UPS-073 | spike §3 unverified: per-recipient calls below 100, no custom header above; switch UNSUBSCRIBE_HEADER_IN_BATCH | Why: plan fallback; one function builds h
- 1794942360 | UPS-074 | non-superadmin preview blind to typed-address dedup/suppression; individual = enrollees only | Why: security review oracle findings; spec §Audiences
- 1794943006 | UPS-073 | marathon: human CODEOWNERS merge | Why: mode rule
- 1794943246 | UPS-074 | sender excluded from own search; club-less admin picks nobody | Why: human decision; keep pages and test assumptions stable; avoid IS NULL match
- 1794949343 | UPS-075 | Footer links %recipient.unsubscribe_url%; UPS-076 should 303 GET to /baja | Why: Mailgun only gets name and unsubscribe_url variables

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
