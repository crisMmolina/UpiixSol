# worklog/WL-1794552753-cris-dev-UPS-065-hack.yM9TfL.md · UPS-065

## Live summary
- Done: PR hero title
- Decision: skeleton title with 2 reserved lines at every width
- Why: UPS-040 no-jump rule; the title wraps on desktop too
- Failing: none
- Commands: Verify; e2e; smoke
- Next: Wait for review

## History
- 1794552753 | CLAIMED | cris-dev | claim; next: red: assert the title on the home in test_sup05, then render it in the hero.
- 1794553641 | REVIEW | cris-dev | done; PR https://github.com/crisMmolina/UpiixSol/pull/117; evidence: Verify exit 0; mobile/flow/layout e2e green; smoke PRODUCT_PASS; design-critic SHIP bc2a9c2 · red at 9344793: E   AssertionError: Locator expected to have text 'Título QA desktop'; reviewer: -
- 1794553652 | REVIEW | cris-dev | checkpoint; next: Wait for review
