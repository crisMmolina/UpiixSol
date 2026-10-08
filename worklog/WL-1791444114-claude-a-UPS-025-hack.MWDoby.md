# worklog/WL-1791444114-claude-a-UPS-025-hack.MWDoby.md · UPS-025

## Live summary
- Done: Claim created; implementation pending
- Decision: Own branch and worktree
- Why: Parallel work without touching the main checkout
- Failing: No validation run yet
- Commands: `uv run pytest -q app/tests/test_community.py app/tests/test_reactions.py && npm --prefix web run build && uv run pytest -q e2e`
- Next: `test_hidden_post_is_redacted`.

## History
- 1791444114 | CLAIMED | claude-a | claim; next: `test_hidden_post_is_redacted`.
- 1791444332 | CLAIMED | claude-a | pending decision UPS-025-1791444332; option: Edit app/schemas/community.py, app/models/community.py, migration 0003, web/src/lib/types.ts, web/src/layouts (nav links) and app/tests/test_academies.py; owners UPS-002/UPS-021/UPS-006 are integrated; Why: plan #35 lists them as owned elsewhere; required for 512 limit, hidden flag, one reaction per user, club-scoped community link
