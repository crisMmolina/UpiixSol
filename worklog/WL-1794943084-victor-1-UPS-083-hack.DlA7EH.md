# worklog/WL-1794943084-victor-1-UPS-083-hack.DlA7EH.md · UPS-083

## Live summary
- Done: fix + tests, PR #130, REVIEW
- Decision: conftest hook sets env_file=None on app.* BaseSettings and gives slowapi an empty config
- Why: dotenv DATABASE_URL pointed to remote Postgres; global engine hit it
- Failing: none open; web lint and build not run (no node_modules)
- Commands: bash .uak/bin/q uv run pytest -q --tb=short -x
- Next: Wait for review: uak wait UPS-083 --for approve

## History
- 1794943084 | CLAIMED | victor-1 | claim; next: reproduce with a throwaway `.env` built from `.env.example`, find the variables, then the stub test and `uak red UPS-083`.
- 1794943122 | CLAIMED | victor-1 | heartbeat; lease until 1794957522
- 1794947869 | CLAIMED | victor-1 | heartbeat; lease until 1794962269
- 1794949021 | CLAIMED | victor-1 | heartbeat; lease until 1794963421
- 1794949376 | REVIEW | victor-1 | done; PR https://github.com/crisMmolina/UpiixSol/pull/130; evidence: bash .uak/bin/q uv run pytest -q --tb=short -x exit 0 with the real dotenv linked; clean detached checkout exit 0 with and without a full throwaway dotenv; ruff ok; coverage 99.96%; the Postgres DATABASE_URL in a dotenv never reaches Settings or app.db under pytest · red at da49359: FAILED app/tests/test_academy_admin.py::test_failed_upload_commit_keeps_previous_logo; reviewer: -
- 1794949390 | REVIEW | victor-1 | checkpoint; next: Wait for review: uak wait UPS-083 --for approve
