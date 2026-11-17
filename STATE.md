# STATE

Phase: execution
Updated: 1794942338
AVAILABLE: UPS-068 UPS-075 UPS-076 UPS-077 UPS-078 UPS-079 UPS-080 UPS-081 UPS-060 
CLAIMED: -
BLOCKED: UPS-057 
REVIEW: UPS-073 UPS-074 UPS-082 
INTEGRATED: (67; last 12) ... UPS-058 UPS-059 UPS-061 UPS-062 UPS-063 UPS-064 UPS-065 UPS-067 UPS-069 UPS-070 UPS-071 UPS-072 
CANCELLED: UPS-030 

Claims (first 24; status --task ID shows detail):
UPS-057 | BLOCKED | david-2 | until 1794548448 (EXPIRED: release --expired --read-summary TOKEN)
UPS-073 | REVIEW | victor-1 | until 1795028652
UPS-074 | REVIEW | victor-2 | until 1795028708
UPS-082 | REVIEW | victor-1 | until 1795028271

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1794936624 | UPS-071 | docs-only, no key used | Why: key in .env unreadable by agents
- 1794938600 | UPS-072 | dropped prod console+enabled rejection (would edit a committed assertion) | Why: security review LOW, spec only requires keys for mailgun
- 1794940895 | UPS-082 | tailwind build-only packages -> devDependencies | Why: no picomatch patch exists (<=4.0.7, first_patched null); --force downgrades vite
- 1794941236 | UPS-074 | academy_admin individual = enrollees only (spec); outside addresses never looked up among users | Why: spec §Audiences; avoid oracle
- 1794942252 | UPS-073 | spike §3 unverified: per-recipient calls below 100, no custom header above; switch UNSUBSCRIBE_HEADER_IN_BATCH | Why: plan fallback; one function builds h

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
