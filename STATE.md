# STATE

Phase: execution
Updated: 1791353499
AVAILABLE: UPS-017 UPS-018 UPS-019 UPS-020 
CLAIMED: UPS-014 UPS-016 
BLOCKED: -
REVIEW: UPS-010 UPS-012 UPS-015 
INTEGRATED: UPS-001 UPS-002 UPS-003 UPS-004 UPS-005 UPS-006 UPS-007 UPS-008 UPS-009 UPS-011 UPS-013 
CANCELLED: -

Claims (first 24; status --task ID shows detail):
UPS-010 | REVIEW | claude-a | until 1791439469
UPS-012 | REVIEW | joahan-claude | until 1791438626
UPS-014 | CLAIMED | claude-a | until 1791366723
UPS-015 | REVIEW | joahan-claude | until 1791439899
UPS-016 | CLAIMED | claude-a | until 1791367499

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1791351367 | UPS-012 | Gestión en /a/:slug/recursos (dentro de Paths); link desde el panel pedido a claude-a | Why: academy-admin/index.tsx es de UPS-008
- 1791352226 | UPS-012 | No merge propio: marathon/PROJECT principio 2 = merge humano CODEOWNER | Why: Aprobación #81 era de 89af2b1
- 1791352323 | UPS-014 | must_change_password stays a non-blocking banner (spec); new session issued on password change | Why: IDEA §2.3 + acceptance
- 1791352408 | deadline decision/UPS-013-1791351460/1791352360 | REVERSIBLE_AND_LOG | Option: UTCDatetime type in app/schemas/common.py used by EventIn (owner UPS-002, already inte
- 1791353499 | UPS-015 | real_ip desde gateway edge 172.31.0.1 + HTTP_BIND loopback obligatorio; red backend internal | Why: Terminador TLS del host llega via docker-proxy: sin rea

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
