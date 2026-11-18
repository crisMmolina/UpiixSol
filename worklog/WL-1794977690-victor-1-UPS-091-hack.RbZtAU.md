# worklog/WL-1794977690-victor-1-UPS-091-hack.RbZtAU.md · UPS-091

## Live summary
- Done: backend image link + GET /api/mail/reply-to; e2e tests red
- Decision: scope widened by victor
- Why: needed for event/image/reply-to
- Failing: none
- Commands: Verify cmd in TASKS.md
- Next: EventBlockEditor, ImageBlockEditor, ReplyToField, wire blocks.ts/Composer/BlockEditor

## History
- 1794977690 | CLAIMED | victor-1 | claim; next: stubs for the e2e Tests names and `uak red UPS-091`; then the event picker, then the image upload, then Reply-To.
- 1794977714 | CLAIMED | victor-1 | heartbeat; lease until 1794992114
- 1794977742 | CLAIMED | victor-1 | pending decision UPS-091-1794977742; option: Also edit web/src/features/mail/blocks.ts, Composer.tsx, EmailPreview.tsx (+ web/src/lib/types.ts if needed, e2e/conftest.py); Why: Paths omit them but event/image kinds, Reply-To state and iframe auto-height live there (UPS-090 left the hooks); no other task touches them
- 1794978762 | CLAIMED | victor-1 | checkpoint; next: EventBlockEditor, ImageBlockEditor, ReplyToField, wire blocks.ts/Composer/BlockEditor
- 1794978919 | CLAIMED | victor-1 | heartbeat; lease until 1794993319
