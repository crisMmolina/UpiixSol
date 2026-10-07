# worklog/WL-1791356171-joahan-claude-UPS-017-hack.dGk11z.md · UPS-017

## Live summary
- Done: Claim created; implementation pending
- Decision: Own branch and worktree
- Why: Parallel work without touching the main checkout
- Failing: No validation run yet
- Commands: `uv run pytest -q app/tests/test_gallery.py app/tests/test_blog.py && npm --prefix web run build`
- Next: `test_draft_project_not_listed`.

## History
- 1791356171 | CLAIMED | joahan-claude | claim; next: `test_draft_project_not_listed`.
