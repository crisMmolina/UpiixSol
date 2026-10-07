# worklog/WL-1791354597-joahan-claude-UPS-018-hack.7qEcjh.md · UPS-018

## Live summary
- Done: API+UI reacciones, matriz 40/40, smoke verde; SHA 9416078
- Decision: mine en endpoint aparte y batch en el cliente: no tocar schemas (UPS-002) ni posts_out
- Why: PostOut no tiene 'mine' y ya trae conteos
- Failing: Scroll horizontal en /comunidad móvil es previo (PR #20); gh sin pull_requests:write
- Commands: uv run pytest -q app/tests/test_reactions.py && npm --prefix web run build
- Next: Review de 9416078; luego UPS-020 cuando UPS-014 esté INTEGRATED

## History
- 1791354597 | CLAIMED | joahan-claude | claim; next: `test_reaction_idempotent`.
- 1791355474 | REVIEW | joahan-claude | done; PR https://github.com/crisMmolina/UpiixSol/pull/new/feat/ups-018; evidence: 9416078: uv run pytest -q app/tests/test_reactions.py (15 passed, 100% cov) && npm --prefix web run build exit 0; smoke PRODUCT_PASS; matrix 40/40 with PUT/DELETE reactions PASSED; Playwright 390+1280: toggle persists after reload, 1 batched /reactions/mine request per page; reviewer: -
- 1791355489 | REVIEW | joahan-claude | checkpoint; next: Review de 9416078; luego UPS-020 cuando UPS-014 esté INTEGRATED
