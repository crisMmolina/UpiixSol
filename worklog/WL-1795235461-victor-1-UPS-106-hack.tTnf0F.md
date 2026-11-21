# worklog/WL-1795235461-victor-1-UPS-106-hack.tTnf0F.md · UPS-106

## Live summary
- Done: Delivery rows endpoint, Spanish reasons, CampaignDetail content+details_purged, matrix row, docs, TS types; PR #169, CI green, security LOW
- Decision: Out-of-scope club 403 like GET /campaigns/{id}; order by id; CampaignDetail only on GET detail
- Why: Matrix and existing test assert 403; id is stable under webhook updates; keeps history list light
- Failing: none
- Commands: bash .uak/bin/q uv run pytest -q --tb=short -x app/tests/test_mail_delivery.py app/tests/test_mail_campaigns.py app/tests/test_permissions_matrix.py
- Next: Wait for review of SHA 32463ecb

## History
- 1795235461 | CLAIMED | victor-1 | claim; next: stubs for the Tests names and `uak red UPS-106`; then the rows endpoint, then reasons, then the campaign content.
- 1795235483 | CLAIMED | victor-1 | heartbeat; lease until 1795249883
- 1795235653 | CLAIMED | victor-1 | pending decision UPS-106-1795235653; option: Another club's campaign gets 403 on the delivery detail (an unknown id gets 404), the same as GET /campaigns/{id}; Why: The task says 404, but GET /campaigns/{id} answers 403 through _load (test_mail_campaigns.py:230) and test_read_matrix expects 403
- 1795236440 | REVIEW | victor-1 | done; PR https://github.com/crisMmolina/UpiixSol/pull/169; evidence: Verify (test_mail_delivery, test_mail_campaigns, test_permissions_matrix) exit 0; smoke exit 0; web build+lint exit 0; CI backend, backend-postgres, web, gates pass; security-reviewer LOW approve 32463ecb; all 4 acceptance criteria met; out-of-scope club 403 per uak decision · red at d2bf415: E   AssertionError: {"error":{"code":"not_found","message":"No encontrado.","details":null}}; reviewer: -
- 1795236459 | REVIEW | victor-1 | checkpoint; next: Wait for review of SHA 32463ecb
