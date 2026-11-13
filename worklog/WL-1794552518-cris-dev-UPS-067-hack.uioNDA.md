# worklog/WL-1794552518-cris-dev-UPS-067-hack.uioNDA.md · UPS-067

## Live summary
- Done: PR reset-password log test
- Decision: caplog at DEBUG
- Why: e2e cannot read server output
- Failing: none
- Commands: Verify; smoke
- Next: Wait for review

## History
- 1794552518 | CLAIMED | cris-dev | claim; next: write the caplog test next to test_reset_password, then the scratch check.
- 1794552730 | REVIEW | cris-dev | done; PR https://github.com/crisMmolina/UpiixSol/pull/116; evidence: Verify exit 0; smoke PRODUCT_PASS; red proven with a never-committed scratch log line · no red: the task says the test passes on today's code; its red was proven with a scratch change (logged password), then reverted; reviewer: -
- 1794552740 | REVIEW | cris-dev | checkpoint; next: Wait for review
