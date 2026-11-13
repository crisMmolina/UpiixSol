# worklog/WL-1794549106-cris-dev-UPS-047-hack.7CsTaW.md · UPS-047

## Live summary
- Done: PR route seed on request
- Decision: Human 2026-11-13: the De cero a LLMs route is seeded only on request (python -m app.seed --ruta-ia / seed(db, ruta_ia=True)), not by default inside seed()
- Why: seeding it by default breaks 11 existing tests and the e2e that rely on one route in UpiixIA (spec open question 1); the human chose the flag in chat; prod runbook keeps it a human step
- Failing: none
- Commands: Verify; suite; smoke
- Next: Integrated in main: a8621b0bf989c7d9e4ddc2f117332d5fb524b453 (recorded by david-3)

## History
- 1794549106 | CLAIMED | cris-dev | claim; next: red fixture and idempotency tests, then the fixture from the spike, then `seed_ruta_ia`.
- 1794549671 | CLAIMED | cris-dev | pending decision UPS-047-1794549671; option: Human 2026-11-13: the De cero a LLMs route is seeded only on request (python -m app.seed --ruta-ia / seed(db, ruta_ia=True)), not by default inside seed(); Why: seeding it by default breaks 11 existing tests and the e2e that rely on one route in UpiixIA (spec open question 1); the human chose the flag in chat; prod runbook keeps it a human step
- 1794550073 | REVIEW | cris-dev | done; PR https://github.com/crisMmolina/UpiixSol/pull/112; evidence: Verify exit 0; seed.py 100%; full suite green; smoke PRODUCT_PASS · red at 4653f79: E   assert (None is not None); reviewer: -
- 1794550083 | REVIEW | cris-dev | checkpoint; next: Wait for review
- 1794550788 | REVIEW | scheduler | deadline decision UPS-047-1794549671; option: Human 2026-11-13: the De cero a LLMs route is seeded only on request (python -m app.seed --ruta-ia / seed(db, ruta_ia=True)), not by default inside seed(); Why: seeding it by default breaks 11 existing tests and the e2e that rely on one route in UpiixIA (spec open question 1); the human chose the flag in chat; prod runbook keeps it a human step
- 1794550920 | REVIEW | david-3 | review; approve; SHA 4a7ce4105bcb99f55a6fc156d36d05e59236e5e9; reviewer david-3
- 1794551014 | INTEGRATED | david-3 | integrate; recorded by david-3; PR https://github.com/crisMmolina/UpiixSol/pull/112; merged a8621b0bf989c7d9e4ddc2f117332d5fb524b453; proof ancestry
