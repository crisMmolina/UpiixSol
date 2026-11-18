# worklog/WL-1794975926-victor-2-UPS-090-hack.TVjx0C.md · UPS-090

## Live summary
- Done: composer, preview, sender, e2e, PR 150
- Decision: board not pickable for club audience (server fallback)
- Why: UPS-089 _sender_club
- Failing: none
- Commands: Verify in TASKS.md
- Next: Wait for review of SHA 37a3bb52

## History
- 1794975926 | CLAIMED | victor-2 | claim; next: after the human `uak allow`, stubs for the e2e Tests names and `uak red UPS-090`; then the block list, then the preview, then the presets.
- 1794975953 | CLAIMED | victor-2 | heartbeat; lease until 1794990353
- 1794977125 | REVIEW | victor-2 | done; PR https://github.com/crisMmolina/UpiixSol/pull/150; evidence: Verify exit 0 (lint, build, 40 e2e passed); smoke exit 0; design-critic SHIP 2d10114; block composer, preview, sender, no test send · existing tests changed with a human's approval (victor) · red at d837948: FAILED e2e/test_mail.py::test_superadmin_sends_to_a_club_after_preview_and_confirm[desktop]; reviewer: -
- 1794977136 | REVIEW | victor-2 | checkpoint; next: Wait for review of SHA 37a3bb52
