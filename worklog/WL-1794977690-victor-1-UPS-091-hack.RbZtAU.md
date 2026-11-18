# worklog/WL-1794977690-victor-1-UPS-091-hack.RbZtAU.md · UPS-091

## Live summary
- Done: Claim created; implementation pending
- Decision: Own branch and worktree
- Why: Parallel work without touching the main checkout
- Failing: No validation run yet
- Commands: `bash .uak/bin/q bash -c 'npm --prefix web run lint && npm --prefix web run build && uv run pytest -q e2e/test_mail_rich.py'`
- Next: stubs for the e2e Tests names and `uak red UPS-091`; then the event picker, then the image upload, then Reply-To.

## History
- 1794977690 | CLAIMED | victor-1 | claim; next: stubs for the e2e Tests names and `uak red UPS-091`; then the event picker, then the image upload, then Reply-To.
- 1794977714 | CLAIMED | victor-1 | heartbeat; lease until 1794992114
- 1794977742 | CLAIMED | victor-1 | pending decision UPS-091-1794977742; option: Also edit web/src/features/mail/blocks.ts, Composer.tsx, EmailPreview.tsx (+ web/src/lib/types.ts if needed, e2e/conftest.py); Why: Paths omit them but event/image kinds, Reply-To state and iframe auto-height live there (UPS-090 left the hooks); no other task touches them
