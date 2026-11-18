# worklog/WL-1794973301-victor-2-UPS-088-hack.jwuF4D.md · UPS-088

## Live summary
- Done: impl+tests+PR 145, REVIEW
- Decision: copy name = sha256(source key)[:32], no table; endpoint allowed for SENDERS
- Why: cache without schema change; spec says academy_admin
- Failing: none
- Commands: bash .uak/bin/q uv run pytest -q --tb=short -x app/tests/test_mail_images.py app/tests/test_media.py app/tests/test_media_storage.py app/tests/test_permissions_matrix.py
- Next: Integrated in main: f896feb913b6f84541e1984f476dc2a4de7cdb99

## History
- 1794973301 | CLAIMED | victor-2 | claim; next: stubs for the Tests names and `uak red UPS-088`; then the media kind, then the endpoint, then `email_copy`.
- 1794973329 | CLAIMED | victor-2 | heartbeat; lease until 1794987729
- 1794973750 | REVIEW | victor-2 | done; PR https://github.com/crisMmolina/UpiixSol/pull/145; evidence: Verify (test_mail_images, test_media, test_media_storage, test_permissions_matrix) exit 0; full suite green; smoke PRODUCT_PASS; all 4 acceptance criteria covered · red at 21774e4: E   assert 404 == 201; reviewer: -
- 1794973788 | REVIEW | victor-2 | checkpoint; next: Wait for review and CI of PR 145
- 1794974127 | REVIEW | victor-1 | review; approve; SHA 747737e56e1df68414f4322eae3d2dec5d5e6403; reviewer victor-1
- 1794974524 | INTEGRATED | victor-2 | merge; smoke and Verify PASS (smoke: full); commit f896feb913b6f84541e1984f476dc2a4de7cdb99; reviewer victor-1
