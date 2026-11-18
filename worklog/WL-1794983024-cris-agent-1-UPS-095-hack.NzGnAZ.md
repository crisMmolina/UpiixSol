# worklog/WL-1794983024-cris-agent-1-UPS-095-hack.NzGnAZ.md · UPS-095

## Live summary
- Done: Claim created; implementation pending
- Decision: Own branch and worktree
- Why: Parallel work without touching the main checkout
- Failing: No validation run yet
- Commands: `bash .uak/bin/q bash -c 'uv run ruff check app && uv run pytest -q --tb=short -x app/tests/test_logo_transparency.py app/tests/test_media.py app/tests/test_media_storage.py app/tests/test_academy_admin.py app/tests/test_permissions_matrix.py && npm --prefix web run lint && npm --prefix web run build'`
- Next: stubs for the `Tests:` names and `uak red UPS-095`; then `remove_white_background` with `ImageDraw.floodfill` on a border-padded mask, the flag in `save_image_bytes`, the form field in the two routers, then the checkbox, preview and button.

## History
- 1794983024 | CLAIMED | cris-agent-1 | claim; next: stubs for the `Tests:` names and `uak red UPS-095`; then `remove_white_background` with `ImageDraw.floodfill` on a border-padded mask, the flag in `save_image_bytes`, the form field in the two routers, then the checkbox, preview and button.
