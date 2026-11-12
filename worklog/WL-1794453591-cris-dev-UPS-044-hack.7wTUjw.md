# worklog/WL-1794453591-cris-dev-UPS-044-hack.7wTUjw.md · UPS-044

## Live summary
- Done: PR #84: boleta-or-email login, generic errors, tests; critic SHIP 7e6e97c
- Decision: human: generic 409 for duplicate boleta; new login error copy
- Why: enumeration-safe registration kept
- Failing: done refused: 4 edited assertions need human allow (msg #333)
- Commands: Verify; pytest --cov=app; smoke
- Next: Human runs uak allow UPS-044 --tests, then uak done UPS-044 --pr .../84

## History
- 1794453591 | CLAIMED | cris-dev | claim; next: schema + service with tests, then the form and the e2e helper.
- 1794453759 | CLAIMED | cris-dev | pending decision UPS-044-1794453759; option: Human 2026-11-12: a duplicate boleta at registration keeps the generic 409 (never says boleta vs email; test_auth.py:74-84 stays); login error becomes 'Boleta, correo o contraseña incorrectos.'; also edits web/src/features/auth/forms.tsx, validation.ts and web/src/lib/types.ts (the login form and its type live there); Why: human answered in chat; enumeration-safe registration kept; same feature folder; no money, accounts, publishing or scope expansion
- 1794454737 | CLAIMED | scheduler | deadline decision UPS-044-1794453759; option: Human 2026-11-12: a duplicate boleta at registration keeps the generic 409 (never says boleta vs email; test_auth.py:74-84 stays); login error becomes 'Boleta, correo o contraseña incorrectos.'; also edits web/src/features/auth/forms.tsx, validation.ts and web/src/lib/types.ts (the login form and its type live there); Why: human answered in chat; enumeration-safe registration kept; same feature folder; no money, accounts, publishing or scope expansion
- 1794455228 | CLAIMED | cris-dev | checkpoint; next: Human runs uak allow UPS-044 --tests, then uak done UPS-044 --pr .../84
