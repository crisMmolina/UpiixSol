# worklog/WL-1794381457-cris-dev-UPS-042-hack.S3b4dn.md · UPS-042

## Live summary
- Done: PR #78: login centered from lg; DESIGN.md rule updated
- Decision: top padding computed once with the mount-time block height; resize recenters with it
- Why: flex centering would move the card top on tab/message changes; full-page screenshots fire resize
- Failing: none
- Commands: Verify; full e2e; smoke
- Next: Wait for review of SHA 75993eb

## History
- 1794381457 | CLAIMED | cris-dev | claim; next: center the main grid with min-h-dvh + content-center only from lg, then the e2e.
- 1794382115 | CLAIMED | cris-dev | pending decision UPS-042-1794382115; option: UPS-042 edits one rule in web/DESIGN.md (owned by integrated UPS-039): the login is centered from lg by a top padding set once, the card top still never moves; Why: design-critic P1: DESIGN.md:72 says the login is never centered, contradicting the change the human asked for; docs only; no money, accounts, publishing or scope expansion
- 1794382159 | REVIEW | cris-dev | done; PR https://github.com/crisMmolina/UpiixSol/pull/78; evidence: Verify exit 0 (x2); full e2e exit 0; smoke PRODUCT_PASS; design-critic SHIP 75993eb · red at c572151: E   AssertionError: above 64 px, below 271 px at 1280×800; reviewer: -
- 1794382168 | REVIEW | cris-dev | checkpoint; next: Wait for review of SHA 75993eb
