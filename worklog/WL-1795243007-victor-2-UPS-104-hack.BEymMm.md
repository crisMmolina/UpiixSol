# worklog/WL-1795243007-victor-2-UPS-104-hack.BEymMm.md · UPS-104

## Live summary
- Done: Gallery, load w/ replace confirm, save dialog, rename/delete, save on send, recent sent, reusar implemented; pushed WIP; e2e mostly green
- Decision: TemplateNameDialog mounts NameForm on open; template origin+sig in ComposerState; Composer.tsx edited (Paths amend requested, msg #618)
- Why: avoid effect racing typing on mobile
- Failing: test_rename_and_delete_own_template: second save_as_template: Guardar button stays disabled aria-busy (dialog still open after first save? ) after NameForm refactor; club_admin test check after fix
- Commands: npm --prefix web run build && uv run pytest -q --tb=short e2e/test_mail_templates.py e2e/test_mail_composer.py
- Next: debug stuck busy Guardar on 2nd save (NameForm: setBusy not reset on success while Modal stays mounted/closing; likely onClose then reopen reuses form), rerun both viewports, then lint, shots .uak-shots/UPS-104 (tests write them), design-critic, /uak-ship

## History
- 1795243007 | CLAIMED | victor-2 | claim; next: stubs for the e2e Tests names and `uak red UPS-104`; then the gallery, then load, then save/rename/delete.
- 1795243032 | CLAIMED | victor-2 | heartbeat; lease until 1795257432
- 1795243909 | CLAIMED | victor-2 | checkpoint; next: fix send tests, shots, design-critic, ship
- 1795244282 | CLAIMED | victor-2 | heartbeat; lease until 1795258682
- 1795244290 | CLAIMED | victor-2 | checkpoint; next: debug stuck busy Guardar on 2nd save (NameForm: setBusy not reset on success while Modal stays mounted/closing; likely onClose then reopen reuses form), rerun both viewports, then lint, shots .uak-shots/UPS-104 (tests write them), design-critic, /uak-ship
- 1795251831 | CLAIMED | victor-2 | heartbeat; lease until 1795266231
