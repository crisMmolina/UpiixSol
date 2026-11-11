# worklog/WL-1794381457-cris-dev-UPS-042-hack.S3b4dn.md · UPS-042

## Live summary
- Done: Claim created; implementation pending
- Decision: Own branch and worktree
- Why: Parallel work without touching the main checkout
- Failing: No validation run yet
- Commands: `npm --prefix web run lint && npm --prefix web run build && uv run pytest -q e2e/test_login_layout.py e2e/test_layout_stability.py`
- Next: center the main grid with min-h-dvh + content-center only from lg, then the e2e.

## History
- 1794381457 | CLAIMED | cris-dev | claim; next: center the main grid with min-h-dvh + content-center only from lg, then the e2e.
- 1794382115 | CLAIMED | cris-dev | pending decision UPS-042-1794382115; option: UPS-042 edits one rule in web/DESIGN.md (owned by integrated UPS-039): the login is centered from lg by a top padding set once, the card top still never moves; Why: design-critic P1: DESIGN.md:72 says the login is never centered, contradicting the change the human asked for; docs only; no money, accounts, publishing or scope expansion
