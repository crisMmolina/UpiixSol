# worklog/WL-1794977690-victor-1-UPS-091-hack.RbZtAU.md · UPS-091

## Live summary
- Done: Verify exit 0 (lint, build, e2e/test_mail_rich.py 10 passed); smoke exit 0; design-critic SHIP ed3861d · existing tests changed with a human's approval (victor) · red at 157d0cf: E   AssertionError: {"error":{"code":"validation_error","message":"Revisa los datos enviados.","details":[{"loc":["body"
- Decision: done blocked by tests-only-grow on 3 e2e/test_mail.py lines
- Why: spec change by design
- Failing: uak done CONFLICT until human allow --tests
- Commands: uak done UPS-091 --pr https://github.com/crisMmolina/UpiixSol/pull/152 --evidence ...
- Next: Humano: New file outside Paths: app/routers/mail_settings.py. Move it into the task's Paths, or a human adds its dir to Additive-Paths in PROJECT.md (new files there need no reservation)

## History
- 1794977690 | CLAIMED | victor-1 | claim; next: stubs for the e2e Tests names and `uak red UPS-091`; then the event picker, then the image upload, then Reply-To.
- 1794977714 | CLAIMED | victor-1 | heartbeat; lease until 1794992114
- 1794977742 | CLAIMED | victor-1 | pending decision UPS-091-1794977742; option: Also edit web/src/features/mail/blocks.ts, Composer.tsx, EmailPreview.tsx (+ web/src/lib/types.ts if needed, e2e/conftest.py); Why: Paths omit them but event/image kinds, Reply-To state and iframe auto-height live there (UPS-090 left the hooks); no other task touches them
- 1794978762 | CLAIMED | victor-1 | checkpoint; next: EventBlockEditor, ImageBlockEditor, ReplyToField, wire blocks.ts/Composer/BlockEditor
- 1794978919 | CLAIMED | victor-1 | heartbeat; lease until 1794993319
- 1794979337 | CLAIMED | victor-1 | checkpoint; next: after human allow --tests, rerun uak done
- 1794980235 | REVIEW | victor-1 | done; PR https://github.com/crisMmolina/UpiixSol/pull/152; evidence: Verify exit 0 (lint, build, e2e/test_mail_rich.py 10 passed); smoke exit 0; design-critic SHIP ed3861d · existing tests changed with a human's approval (victor) · red at 157d0cf: E   AssertionError: {"error":{"code":"validation_error","message":"Revisa los datos enviados.","details":[{"loc":["body"; reviewer: -
- 1794980245 | REVIEW | victor-1 | heartbeat; lease until 1795066645
- 1794980581 | REVIEW | victor-3 | review; approve; SHA dc7fd8448903b38f9e7473a524d85d3b570fe45c; reviewer victor-3
- 1794980659 | REVIEW | victor-1 | merge rechazado; New file outside Paths: app/routers/mail_settings.py. Move it into the task's Paths, or a human adds its dir to Additive-Paths in PROJECT.md (new files there need no reservation)
