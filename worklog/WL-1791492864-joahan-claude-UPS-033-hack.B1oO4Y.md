# worklog/WL-1791492864-joahan-claude-UPS-033-hack.B1oO4Y.md · UPS-033

## Live summary
- Done: Primitives in web/src/components (FormMessage reserved slot, Field reserve, AnimatedHeight, Stagger/StaggerItem, Modal/Drawer enter-exit top-anchored, fieldErrors in Spanish); /login top-anchored card, animated tab switch, client validation, 429 wait text; /cuenta single status per tab, reserved lines, disabled-button reasons, avatar checks; DESIGN.md Movimiento y estabilidad; e2e/test_layout_stability.py. Role guard: not reproducible (URL changes once /api/auth/refresh resolves; audit read page.url early), pinned by e2e, lib/auth.tsx unchanged
- Decision: -
- Why: -
- Failing: -
- Commands: npm --prefix web run lint (0 errors; my files 12->6 warnings, none new) · npm --prefix web run build (ok) · uv run pytest -q e2e (21 passed, 1 skipped)
- Next: review

## History
- 1791492864 | CLAIMED | joahan-claude | claim; next: build the primitives, then apply them to auth and account.
- 1791495048 | CLAIMED | joahan-claude | checkpoint; next: review
