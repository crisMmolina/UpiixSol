# worklog/WL-1794537259-cris-dev-UPS-061-hack.MwU4Kk.md · UPS-061

## Live summary
- Done: PR focus trap in Overlay
- Decision: keydown trap; skip controls in closed details via checkVisibility
- Why: native showModal lets Tab leave; closed details links still report rects
- Failing: test_mobile panel Recursos flake under full suite (passes alone)
- Commands: Verify; e2e; smoke
- Next: Wait for review

## History
- 1794537259 | CLAIMED | cris-dev | claim; next: red e2e that tabs through the "Más" drawer and the "Nuevo evento" modal, then a keydown trap in Overlay.tsx.
- 1794538260 | REVIEW | cris-dev | done; PR https://github.com/crisMmolina/UpiixSol/pull/103; evidence: Verify exit 0 (x2); smoke PRODUCT_PASS; design-critic SHIP b64f3a5 · red at 4862c7f: E   AssertionError: Tab #3 took focus out of the dialog; reviewer: -
- 1794538274 | REVIEW | cris-dev | checkpoint; next: Wait for review
