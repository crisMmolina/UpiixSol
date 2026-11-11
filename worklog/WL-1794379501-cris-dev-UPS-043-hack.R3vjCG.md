# worklog/WL-1794379501-cris-dev-UPS-043-hack.R3vjCG.md · UPS-043

## Live summary
- Done: drawer fix + frame-sampling e2e; PR #77
- Decision: dialog overflow-clip; panel exits before the backdrop; dialog closes on backdrop exit
- Why: overflow-hidden dialog scrolled sideways when showModal focused the off-screen close button (scrollLeft 343)
- Failing: none
- Commands: Verify; e2e full; WebKit run of test_drawer_motion
- Next: Wait for review of SHA 3a3a115

## History
- 1794379501 | CLAIMED | cris-dev | claim; next: reproduce with a frame-sampling e2e (red), then fix the dialog's initial position/animation in Overlay.tsx.
- 1794381328 | CLAIMED | cris-dev | checkpoint; next: Wait for review of SHA 3a3a115
