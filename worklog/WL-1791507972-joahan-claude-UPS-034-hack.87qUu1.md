# worklog/WL-1791507972-joahan-claude-UPS-034-hack.87qUu1.md · UPS-034

## Live summary
- Done: drafts-only API filter (blog/gallery) + tests; calendar: request-keyed data (skeleton, no stale rows), ?dia= drives month, month change clears day, fixed cell height with +N, phone dot+count, day detail scrolls into view; event form field errors (reserve/FormMessage); Más recientes; Modal open={x} in blog/gallery/events; e2e/test_content.py
- Decision: -
- Why: -
- Failing: -
- Commands: pytest app/tests/test_blog.py test_gallery.py: pass; pytest --cov=app: TOTAL 100%; ruff check/format: ok; npm run lint: no new warnings; npm run build: ok; pytest -q e2e: 39 passed 1 skipped
- Next: review

## History
- 1791507972 | CLAIMED | joahan-claude | claim; next: fix the calendar state, then the loading swaps, then drafts.
- 1791509508 | CLAIMED | joahan-claude | checkpoint; next: review
