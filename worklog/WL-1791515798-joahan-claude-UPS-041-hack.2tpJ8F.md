# worklog/WL-1791515798-joahan-claude-UPS-041-hack.2tpJ8F.md · UPS-041

## Live summary
- Done: site_settings singleton + migration 0006; GET /api/site public (60s cache), PUT/POST/DELETE /api/admin/site[/logo|/mascot] superadmin; matrix rows + docs; lib/brand.tsx runtime store (top-level await <=800ms, applySite, useSite); App.tsx remounts routes on brand change; /admin tab Marca del sitio with live preview; e2e/test_site_brand.py
- Decision: -
- Why: -
- Failing: -
- Commands: ruff check app OK; pytest --cov=app 100%; alembic up/down/up on postgres:16 OK; web lint 0 new warnings; web build OK; pytest e2e 67 passed 1 skipped
- Next: review

## History
- 1791515798 | CLAIMED | joahan-claude | claim; next: model + migration + API, then the web store and the admin tab.
- 1791517578 | CLAIMED | joahan-claude | checkpoint; next: review
