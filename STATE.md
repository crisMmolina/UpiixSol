# STATE

Phase: execution
Updated: 1791355506
AVAILABLE: UPS-017 UPS-019 UPS-020 
CLAIMED: -
BLOCKED: -
REVIEW: UPS-012 UPS-014 UPS-015 UPS-016 UPS-018 
INTEGRATED: UPS-001 UPS-002 UPS-003 UPS-004 UPS-005 UPS-006 UPS-007 UPS-008 UPS-009 UPS-010 UPS-011 UPS-013 
CANCELLED: -

Claims (first 24; status --task ID shows detail):
UPS-012 | REVIEW | joahan-claude | until 1791440520
UPS-014 | REVIEW | claude-a | until 1791440918
UPS-015 | REVIEW | joahan-claude | until 1791439899
UPS-016 | REVIEW | claude-a | until 1791440577
UPS-018 | REVIEW | joahan-claude | until 1791441889

Blockers: BLOCKED tasks; use status --task ID --summary.
Current decisions (last 5):
- 1791352323 | UPS-014 | must_change_password stays a non-blocking banner (spec); new session issued on password change | Why: IDEA §2.3 + acceptance
- 1791352408 | deadline decision/UPS-013-1791351460/1791352360 | REVERSIBLE_AND_LOG | Option: UTCDatetime type in app/schemas/common.py used by EventIn (owner UPS-002, already inte
- 1791353499 | UPS-015 | real_ip desde gateway edge 172.31.0.1 + HTTP_BIND loopback obligatorio; red backend internal | Why: Terminador TLS del host llega via docker-proxy: sin rea
- 1791355489 | UPS-018 | mine en endpoint aparte y batch en el cliente: no tocar schemas (UPS-002) ni posts_out | Why: PostOut no tiene 'mine' y ya trae conteos
- 1791355506 | deadline decision/UPS-014-1791354509/1791355409 | REVERSIBLE_AND_LOG | Option: Regenerate docs/permissions-matrix.md (owner UPS-010, integrated, same author) in the 

Global next step: available P0; else review PRs, tests, demo, rehearsal.
Why: bounded snapshot to resume without rereading history.
