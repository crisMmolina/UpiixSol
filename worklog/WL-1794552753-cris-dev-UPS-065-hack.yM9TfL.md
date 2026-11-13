# worklog/WL-1794552753-cris-dev-UPS-065-hack.yM9TfL.md · UPS-065

## Live summary
- Done: Claim created; implementation pending
- Decision: Own branch and worktree
- Why: Parallel work without touching the main checkout
- Failing: No validation run yet
- Commands: `npm --prefix web run build && uv run pytest -q e2e/test_qa_admin.py`
- Next: red: assert the title on the home in test_sup05, then render it in the hero.

## History
- 1794552753 | CLAIMED | cris-dev | claim; next: red: assert the title on the home in test_sup05, then render it in the hero.
