# worklog/WL-1791515798-joahan-claude-UPS-041-hack.2tpJ8F.md · UPS-041

## Live summary
- Done: review fixes: auth/home useSite; late brand no remount until next navigation; page.view dedupe; no mascot img when none; bidi controls rejected; compare-and-swap logo/mascot; e2e late-brand + logout + page view count
- Decision: Review fix for UPS-041 edits web/src/features/auth/index.tsx and web/src/features/home/index.tsx (in UPS-040's Paths, not claimed) so the login and home read the live site brand
- Why: 8aabe37 was merged (#66) before review; reviewer rejected: login keeps module-load colors
- Failing: -
- Commands: ruff OK; pytest --cov=app 100%; web lint 0 new; build OK; pytest e2e 69 passed 1 skipped
- Next: Recover lease with token; then apply option: Review fix for UPS-041 edits web/src/features/auth/index.tsx and web/src/features/home/index.tsx (in UPS-040's Paths, not claimed) so the login and home read the live site brand

## History
- 1791515798 | CLAIMED | joahan-claude | claim; next: model + migration + API, then the web store and the admin tab.
- 1791517578 | CLAIMED | joahan-claude | checkpoint; next: review
- 1791517625 | REVIEW | joahan-claude | done; PR https://github.com/crisMmolina/UpiixSol/pull/new/feat/ups-041; evidence: 8aabe37: pytest 100 %, e2e 67 passed 1 skipped, PG 0006 up/down/up; reviewer: -
- 1791530092 | REVIEW | joahan-rev | review; reject; SHA 8aabe37af1d8bacb93366ca368ab7ac4a841d9e1; reviewer joahan-rev
- 1791530147 | REVIEW | joahan-claude | heartbeat; lease until 1791616547
- 1791530155 | REVIEW | joahan-claude | pending decision UPS-041-1791530155; option: Review fix for UPS-041 edits web/src/features/auth/index.tsx and web/src/features/home/index.tsx (in UPS-040's Paths, not claimed) so the login and home read the live site brand; Why: 8aabe37 was merged (#66) before review; reviewer rejected: login keeps module-load colors
- 1791531123 | REVIEW | joahan-claude | checkpoint; next: review
- 1791531748 | REVIEW | joahan-rev | review; approve; SHA 2bd97c5daf98baff406dd23e48663d02f187b541; reviewer joahan-rev
- 1794354344 | REVIEW | scheduler | deadline decision UPS-041-1791530155; option: Review fix for UPS-041 edits web/src/features/auth/index.tsx and web/src/features/home/index.tsx (in UPS-040's Paths, not claimed) so the login and home read the live site brand; Why: 8aabe37 was merged (#66) before review; reviewer rejected: login keeps module-load colors
- 1794374944 | AVAILABLE | cris-dev | release; claim released by cris-dev; reason: -; summary kept
- 1794374954 | CLAIMED | cris-dev | claim; next: Recover lease with token; then apply option: Review fix for UPS-041 edits web/src/features/auth/index.tsx and web/src/features/home/index.tsx (in UPS-040's Paths, not claimed) so the login and home read the live site brand
