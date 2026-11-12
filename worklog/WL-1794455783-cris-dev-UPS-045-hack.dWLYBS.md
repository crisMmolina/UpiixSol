# worklog/WL-1794455783-cris-dev-UPS-045-hack.dWLYBS.md · UPS-045

## Live summary
- Done: Claim created; implementation pending
- Decision: Own branch and worktree
- Why: Parallel work without touching the main checkout
- Failing: No validation run yet
- Commands: `uv run pytest -q app/tests/test_youtube.py app/tests/test_academy_admin.py app/tests/test_learning.py app/tests/test_permissions_matrix.py && uv run ruff check app && uv run alembic upgrade head && uv run alembic downgrade base`
- Next: red tests for `parse_start` and `embed_url`, then migration and model, then admin save and lesson output.

## History
- 1794455783 | CLAIMED | cris-dev | claim; next: red tests for `parse_start` and `embed_url`, then migration and model, then admin save and lesson output.
- 1794456491 | CLAIMED | cris-dev | pending decision UPS-045-1794456491; option: UPS-045 also changes playerSrc() in web/src/features/learning/youtube.ts (in UPS-048 Paths, not claimed) to merge params with new URL(); Why: with UPS-045 alone, a lesson saved with ?t= gets embed_url ...?start=N and playerSrc appends ?enablejsapi=1 → broken URL and no completion tracking; UPS-048 cannot be claimed until UPS-045 is integrated; one line, plan.md §Design 1 prescribes it; no money, accounts, publishing or scope expansion
