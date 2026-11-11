# worklog/WL-1794379501-cris-dev-UPS-043-hack.R3vjCG.md · UPS-043

## Live summary
- Done: Verify exit 0; full e2e exit 0; WebKit and Chromium green on e2e/test_drawer_motion.py; smoke PRODUCT_PASS; design-critic SHIP · red at c572151: E   AssertionError: opening frame 0: panel on screen without the backdrop
- Decision: dialog overflow-clip; panel exits before the backdrop; dialog closes on backdrop exit
- Why: overflow-hidden dialog scrolled sideways when showModal focused the off-screen close button (scrollLeft 343)
- Failing: none
- Commands: Verify; e2e full; WebKit run of test_drawer_motion
- Next: Another agent reviews https://github.com/crisMmolina/UpiixSol/pull/77; run .uak/bin/smoke

## History
- 1794379501 | CLAIMED | cris-dev | claim; next: reproduce with a frame-sampling e2e (red), then fix the dialog's initial position/animation in Overlay.tsx.
- 1794381328 | CLAIMED | cris-dev | checkpoint; next: Wait for review of SHA 3a3a115
- 1794381433 | REVIEW | cris-dev | done; PR https://github.com/crisMmolina/UpiixSol/pull/77; evidence: Verify exit 0; full e2e exit 0; WebKit and Chromium green on e2e/test_drawer_motion.py; smoke PRODUCT_PASS; design-critic SHIP · red at c572151: E   AssertionError: opening frame 0: panel on screen without the backdrop; reviewer: -
