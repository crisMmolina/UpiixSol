# worklog/WL-1791351730-claude-a-UPS-014-hack.lSvUFE.md · UPS-014

## Live summary
- Done: API account + /cuenta UI; pytest cov 100%; smoke ok; browser: wrong pwd error, change ok, session survives reload
- Decision: must_change_password stays a non-blocking banner (spec); new session issued on password change
- Why: IDEA §2.3 + acceptance
- Failing: none
- Commands: uv run pytest -q app/tests/test_account.py && npm --prefix web run build
- Next: security review of 3973438, then PR

## History
- 1791351730 | CLAIMED | claude-a | claim; next: `test_change_password_requires_current`.
- 1791352323 | CLAIMED | claude-a | checkpoint; next: security review of 3973438, then PR
