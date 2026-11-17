# worklog/WL-1794954358-victor-2-UPS-081-hack.HyzqZ7.md · UPS-081

## Live summary
- Done: purge + CLI, 4 tests green, PR 137
- Decision: finished_at cutoff; snapshot only when rows exist
- Why: second run must not zero the snapshot
- Failing: none
- Commands: bash .uak/bin/q uv run pytest -q --tb=short -x app/tests/test_mail_retention.py
- Next: Wait for review of SHA 3cd51404

## History
- 1794954358 | CLAIMED | victor-2 | claim; next: stubs for the Tests names and `uak red UPS-081`; then the query, then the CLI.
- 1794954392 | CLAIMED | victor-2 | heartbeat; lease until 1794968792
- 1794954576 | REVIEW | victor-2 | done; PR https://github.com/crisMmolina/UpiixSol/pull/137; evidence: pytest app/tests/test_mail_retention.py exit 0; smoke exit 0; 4 criteria tests green · red at 3dfd350: FAILED app/tests/test_mail_retention.py::test_purge_deletes_recipients_of_old_campaigns_only; reviewer: -
- 1794954588 | REVIEW | victor-2 | checkpoint; next: Wait for review of SHA 3cd51404
