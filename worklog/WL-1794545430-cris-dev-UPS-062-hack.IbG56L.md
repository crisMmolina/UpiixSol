# worklog/WL-1794545430-cris-dev-UPS-062-hack.IbG56L.md · UPS-062

## Live summary
- Done: Claim created; implementation pending
- Decision: Own branch and worktree
- Why: Parallel work without touching the main checkout
- Failing: No validation run yet
- Commands: `uv run pytest -q app/tests/test_learning.py app/tests/test_analytics.py app/tests/test_permissions_matrix.py`
- Next: red test that DELETE answers 405, then remove the endpoint and the dead code, then fix the tests that used it.

## History
- 1794545430 | CLAIMED | cris-dev | claim; next: red test that DELETE answers 405, then remove the endpoint and the dead code, then fix the tests that used it.
- 1794545555 | CLAIMED | cris-dev | pending decision UPS-062-1794545555; option: UPS-062 also edits app/services/analytics.py and docs/analytics.md (drop the lesson.uncompleted event of the removed route) and app/tests/test_progress.py (it imported the removed uncomplete_lesson); Why: the acceptance asks for no dead code after removing DELETE /lessons/{id}/complete; same feature; no money, accounts, publishing or scope expansion
