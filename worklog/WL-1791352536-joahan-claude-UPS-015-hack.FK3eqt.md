# worklog/WL-1791352536-joahan-claude-UPS-015-hack.FK3eqt.md · UPS-015

## Live summary
- Done: merged #32; approved d8a86d4 by joahan-2
- Decision: real_ip desde gateway edge 172.31.0.1 + HTTP_BIND loopback obligatorio; red backend internal
- Why: Terminador TLS del host llega via docker-proxy: sin real_ip todos comparten llave de rate limit
- Failing: gh sin permiso createPullRequest; pendiente: server_name/HSTS dependen del dominio (hosting sin decidir)
- Commands: docker compose config -q && bash -n deploy/backup.sh
- Next: Integrated in main: 9b60e020781259ea5420729c39413614c58ca157; claim next P0

## History
- 1791352536 | CLAIMED | joahan-claude | claim; next: multi-stage `Dockerfile` (node build → python runtime).
- 1791353491 | REVIEW | joahan-claude | done; PR https://github.com/crisMmolina/UpiixSol/pull/new/feat/ups-015; evidence: c5857e1: docker compose config -q && bash -n deploy/backup.sh exit 0; smoke PRODUCT_PASS; live stack on Postgres 16: 3 services healthy, migrations+seed, nginx headers/SPA/media CSP+cache, 7MB→413, per-client rate limit (A 429 after 5, B unaffected, injected XFF ignored), api no internet, backup+restore rehearsed; security-reviewer MEDIUMs fixed+retested; reviewer: -
- 1791353499 | REVIEW | joahan-claude | checkpoint; next: Review de c5857e1; PR lo abre el humano
- 1791354731 | REVIEW | claude | review; approve; SHA c5857e149fe5dcbe9e65e8f9a614226082a247c8; reviewer claude
- 1791444562 | REVIEW | joahan-claude | heartbeat; lease until 1791530962
- 1791450801 | REVIEW | joahan-claude | heartbeat; lease until 1791537201
- 1791454853 | REVIEW | joahan-claude | heartbeat; lease until 1791541253
- 1791455563 | REVIEW | joahan-claude | heartbeat; lease until 1791541963
- 1791456266 | REVIEW | joahan-claude | heartbeat; lease until 1791542666
- 1791456977 | REVIEW | joahan-claude | heartbeat; lease until 1791543377
- 1791457684 | REVIEW | joahan-claude | heartbeat; lease until 1791544084
- 1791458388 | REVIEW | joahan-claude | heartbeat; lease until 1791544788
- 1791459093 | REVIEW | joahan-claude | heartbeat; lease until 1791545493
- 1791469584 | REVIEW | joahan-claude | heartbeat; lease until 1791555984
- 1791470287 | REVIEW | joahan-claude | heartbeat; lease until 1791556687
- 1791470990 | REVIEW | joahan-claude | heartbeat; lease until 1791557390
- 1791470992 | REVIEW | joahan-2 | review; approve; SHA d8a86d40d2f8b32a500790a07138b76dd8604ed1; reviewer joahan-2
- 1791471107 | INTEGRATED | joahan-claude | done; PR https://github.com/crisMmolina/UpiixSol/pull/32; evidence: merged #32; approved d8a86d4 by joahan-2; reviewer: joahan-2
