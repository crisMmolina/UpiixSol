# worklog/WL-1794976139-cris-agent-1-UPS-093-hack.Nr9wZ5.md · UPS-093

## Live summary
- Done: Claim created; implementation pending
- Decision: Own branch and worktree
- Why: Parallel work without touching the main checkout
- Failing: No validation run yet
- Commands: `bash .uak/bin/q bash -c 'uv run ruff check app && uv run pytest -q --tb=short -x app/tests/test_admin_roles.py app/tests/test_admin.py app/tests/test_permissions_matrix.py && npm --prefix web run lint && npm --prefix web run build'`
- Next: stubs for the `Tests:` names and `uak red UPS-093`; then `change_role` in `app/services/admin.py`, the route and schema, the matrix row, then the Usuarios tab.

## History
- 1794976139 | CLAIMED | cris-agent-1 | claim; next: stubs for the `Tests:` names and `uak red UPS-093`; then `change_role` in `app/services/admin.py`, the route and schema, the matrix row, then the Usuarios tab.
