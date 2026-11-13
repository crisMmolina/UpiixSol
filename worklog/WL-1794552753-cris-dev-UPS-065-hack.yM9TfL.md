# worklog/WL-1794552753-cris-dev-UPS-065-hack.yM9TfL.md · UPS-065

## Live summary
- Done: PR hero title
- Decision: skeleton title with 2 reserved lines at every width
- Why: UPS-040 no-jump rule; the title wraps on desktop too
- Failing: none
- Commands: Verify; e2e; smoke
- Next: Integrated in main: 4e3b175ba7601566a88cf9b6c5309d7186fa5401 (recorded by david-8)

## History
- 1794552753 | CLAIMED | cris-dev | claim; next: red: assert the title on the home in test_sup05, then render it in the hero.
- 1794553641 | REVIEW | cris-dev | done; PR https://github.com/crisMmolina/UpiixSol/pull/117; evidence: Verify exit 0; mobile/flow/layout e2e green; smoke PRODUCT_PASS; design-critic SHIP bc2a9c2 · red at 9344793: E   AssertionError: Locator expected to have text 'Título QA desktop'; reviewer: -
- 1794553652 | REVIEW | cris-dev | checkpoint; next: Wait for review
- 1794554087 | REVIEW | david-8 | review; approve; SHA bc2a9c27948960f71c0814809af3db65efb8825d; reviewer david-8
- 1794554261 | INTEGRATED | david-8 | integrate; recorded by david-8; PR https://github.com/crisMmolina/UpiixSol/pull/117; merged 4e3b175ba7601566a88cf9b6c5309d7186fa5401; proof ancestry
