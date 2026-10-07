# STATE

Phase: execution
Updated: 1791357586
AVAILABLE: UPS-020 
CLAIMED: UPS-017 
BLOCKED: -
REVIEW: UPS-012 UPS-014 UPS-015 UPS-016 UPS-018 UPS-019 
INTEGRATED: UPS-001 UPS-002 UPS-003 UPS-004 UPS-005 UPS-006 UPS-007 UPS-008 UPS-009 UPS-010 UPS-011 UPS-013 
CANCELLED: -

Claims (first 24; status --task ID shows detail):
UPS-012 | REVIEW | joahan-claude | until 1791440520
UPS-014 | REVIEW | claude-a | until 1791440918
UPS-015 | REVIEW | joahan-claude | until 1791439899
UPS-016 | REVIEW | claude-a | until 1791440577
UPS-017 | CLAIMED | joahan-claude | until 1791370571
UPS-018 | REVIEW | joahan-claude | until 1791443986
UPS-019 | REVIEW | joahan-claude | until 1791442522

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1791352408 | deadline decision/UPS-013-1791351460/1791352360 | REVERSIBLE_AND_LOG | Option: UTCDatetime type in app/schemas/common.py used by EventIn (owner UPS-002, already inte
- 1791353499 | UPS-015 | real_ip desde gateway edge 172.31.0.1 + HTTP_BIND loopback obligatorio; red backend internal | Why: Terminador TLS del host llega via docker-proxy: sin rea
- 1791355489 | UPS-018 | mine en endpoint aparte y batch en el cliente: no tocar schemas (UPS-002) ni posts_out | Why: PostOut no tiene 'mine' y ya trae conteos
- 1791355506 | deadline decision/UPS-014-1791354509/1791355409 | REVERSIBLE_AND_LOG | Option: Regenerate docs/permissions-matrix.md (owner UPS-010, integrated, same author) in the 
- 1791356122 | UPS-019 | HTML5 DnD nativo sin dependencia; rutas siguen solo con flechas (criterio pide módulos y clases) | Why: Paso siguiente del backlog: evaluar sin dependenci

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
