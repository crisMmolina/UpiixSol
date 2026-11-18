# worklog/WL-1794980386-cris-agent-1-UPS-094-hack.vG4saV.md · UPS-094

## Live summary
- Done: Claim created; implementation pending
- Decision: Own branch and worktree
- Why: Parallel work without touching the main checkout
- Failing: No validation run yet
- Commands: `bash .uak/bin/q bash -c 'uv run ruff check app && uv run pytest -q --tb=short -x app/tests/test_event_cover.py app/tests/test_events.py app/tests/test_permissions_matrix.py && npm --prefix web run lint && npm --prefix web run build'`
- Next: stubs for the `Tests:` names and `uak red UPS-094`; then `replace_cover` and `remove_cover` in `app/services/events.py` copying the blog cover flow, the two routes, the matrix rows, then the form field and the cards.

## History
- 1794980386 | CLAIMED | cris-agent-1 | claim; next: stubs for the `Tests:` names and `uak red UPS-094`; then `replace_cover` and `remove_cover` in `app/services/events.py` copying the blog cover flow, the two routes, the matrix rows, then the form field and the cards.
