# worklog/WL-1794949986-victor-2-UPS-078-hack.xzbeNE.md · UPS-078

## Live summary
- Done: Correos tab: Composer, AudiencePicker, History, confirm modal; e2e 12 passed
- Decision: Own mail_env fixture in e2e/test_mail.py (MAIL_ENABLED, unblocked domain, seed password)
- Why: conftest untouched
- Failing: none
- Commands: bash .uak/bin/q bash -c 'npm --prefix web run lint && npm --prefix web run build && uv run pytest -q e2e/test_mail.py'
- Next: screenshots in .uak-shots/UPS-078, design-critic SHIP, then /uak-ship

## History
- 1794949986 | CLAIMED | victor-2 | claim; next: stubs for the e2e Tests names and `uak red UPS-078`; then `AudiencePicker`, then the confirm modal, then history.
- 1794950016 | CLAIMED | victor-2 | heartbeat; lease until 1794964416
- 1794950373 | CLAIMED | victor-2 | checkpoint; next: screenshots in .uak-shots/UPS-078, design-critic SHIP, then /uak-ship
