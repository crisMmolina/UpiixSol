# worklog/WL-1795230569-victor-1-UPS-101-hack.JlZs8G.md · UPS-101

## Live summary
- Done: Templates API, preview theme and render-only, placeholder 422 on create/send, matrix and doc; PR 167 CI green
- Decision: Plain array list per plan Contracts; superadmin manages every template; out-of-scope id 403 per spec
- Why: Task criteria outrank the generic pagination rule; spec asks for 403
- Failing: none
- Commands: bash .uak/bin/q uv run pytest -q --tb=short -x app/tests/test_mail_templates.py app/tests/test_mail_preview.py app/tests/test_permissions_matrix.py
- Next: Integrated in main: ae798a1acd55d7e92bdad68306ac51e99e0f5960

## History
- 1795230569 | CLAIMED | victor-1 | claim; next: stubs for the Tests names and `uak red UPS-101`; then list, then save, then rename/delete, then the preview theme.
- 1795230597 | CLAIMED | victor-1 | heartbeat; lease until 1795244997
- 1795231861 | CLAIMED | victor-1 | heartbeat; lease until 1795246261
- 1795231868 | REVIEW | victor-1 | done; PR https://github.com/crisMmolina/UpiixSol/pull/167; evidence: Verify exit 0; smoke exit 0 PRODUCT_PASS; full suite clean worktree exit 0 cov 99% (new modules 100%); CI backend, backend-postgres, gates, web pass; security-reviewer LOW only (overflow id fixed); all criteria met · red at ca0ea2a: E   AssertionError: {"error":{"code":"not_found","message":"No encontrado.","details":null}}; reviewer: -
- 1795231876 | REVIEW | victor-1 | checkpoint; next: Wait for review of SHA 29e1651
- 1795232322 | REVIEW | victor-3 | review; approve; SHA 29e165139c9aef872b61f35c7fd589846a1c194b; reviewer victor-3
- 1795232980 | INTEGRATED | victor-1 | merge; smoke and Verify PASS (smoke: full); commit ae798a1acd55d7e92bdad68306ac51e99e0f5960; reviewer victor-3
