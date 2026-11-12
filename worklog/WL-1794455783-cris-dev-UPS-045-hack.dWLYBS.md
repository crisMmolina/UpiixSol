# worklog/WL-1794455783-cris-dev-UPS-045-hack.dWLYBS.md · UPS-045

## Live summary
- Done: PR #85: segments API + migration 0007 + playerSrc merge fix
- Decision: UPS-045 also changes playerSrc() in web/src/features/learning/youtube.ts (in UPS-048 Paths, not claimed) to merge params with new URL()
- Why: with UPS-045 alone, a lesson saved with ?t= gets embed_url ...?start=N and playerSrc appends ?enablejsapi=1 → broken URL and no completion tracking; UPS-048 cannot be claimed until UPS-045 is integrated; one line, plan.md §Design 1 prescribes it; no money, accounts, publishing or scope expansion
- Failing: none
- Commands: Verify; pytest --cov=app; e2e; smoke
- Next: Apply option: UPS-045 also changes playerSrc() in web/src/features/learning/youtube.ts (in UPS-048 Paths, not claimed) to merge params with new URL()

## History
- 1794455783 | CLAIMED | cris-dev | claim; next: red tests for `parse_start` and `embed_url`, then migration and model, then admin save and lesson output.
- 1794456491 | CLAIMED | cris-dev | pending decision UPS-045-1794456491; option: UPS-045 also changes playerSrc() in web/src/features/learning/youtube.ts (in UPS-048 Paths, not claimed) to merge params with new URL(); Why: with UPS-045 alone, a lesson saved with ?t= gets embed_url ...?start=N and playerSrc appends ?enablejsapi=1 → broken URL and no completion tracking; UPS-048 cannot be claimed until UPS-045 is integrated; one line, plan.md §Design 1 prescribes it; no money, accounts, publishing or scope expansion
- 1794456707 | REVIEW | cris-dev | done; PR https://github.com/crisMmolina/UpiixSol/pull/85; evidence: Verify exit 0; pytest --cov=app 100% (alembic check); full e2e exit 0; smoke PRODUCT_PASS; design-critic SHIP 5bfdfc9 · red at a16cdc1: E   AssertionError: assert None == 850; reviewer: -
- 1794456719 | REVIEW | cris-dev | checkpoint; next: Wait for review of SHA 5bfdfc9
- 1794458486 | REVIEW | scheduler | deadline decision UPS-045-1794456491; option: UPS-045 also changes playerSrc() in web/src/features/learning/youtube.ts (in UPS-048 Paths, not claimed) to merge params with new URL(); Why: with UPS-045 alone, a lesson saved with ?t= gets embed_url ...?start=N and playerSrc appends ?enablejsapi=1 → broken URL and no completion tracking; UPS-048 cannot be claimed until UPS-045 is integrated; one line, plan.md §Design 1 prescribes it; no money, accounts, publishing or scope expansion
