# worklog/WL-1795243007-victor-2-UPS-104-hack.BEymMm.md · UPS-104

## Live summary
- Done: bash .uak/bin/q bash -c 'npm --prefix web run lint && npm --prefix web run build && uv run pytest -q e2e/test_mail_templates.py e2e/test_mail_composer.py' exit 0 (34 passed); design-critic SHIP 747fdd6 (a662204 only changes an e2e shot); shots 1280 and 390 · red at ec85f41: FAILED e2e/test_mail_templates.py::test_gallery_shows_builtins_saved_and_blank_with_thumbnails[desktop]
- Decision: Composer.tsx edited outside Paths: merge gate sends it to the human
- Why: save on send and template load hook into its confirm()
- Failing: none open; e2e composer 390 test flaked twice under load, passes alone
- Commands: bash .uak/bin/q bash -c 'npm --prefix web run lint && npm --prefix web run build && uv run pytest -q e2e/test_mail_templates.py e2e/test_mail_composer.py'
- Next: Integrated in main: 1f35f8c6a588e69d84f4c2dbffa269a8ce7a70a9 (recorded by victor-2)

## History
- 1795243007 | CLAIMED | victor-2 | claim; next: stubs for the e2e Tests names and `uak red UPS-104`; then the gallery, then load, then save/rename/delete.
- 1795243032 | CLAIMED | victor-2 | heartbeat; lease until 1795257432
- 1795243909 | CLAIMED | victor-2 | checkpoint; next: fix send tests, shots, design-critic, ship
- 1795244282 | CLAIMED | victor-2 | heartbeat; lease until 1795258682
- 1795244290 | CLAIMED | victor-2 | checkpoint; next: debug stuck busy Guardar on 2nd save (NameForm: setBusy not reset on success while Modal stays mounted/closing; likely onClose then reopen reuses form), rerun both viewports, then lint, shots .uak-shots/UPS-104 (tests write them), design-critic, /uak-ship
- 1795251831 | CLAIMED | victor-2 | heartbeat; lease until 1795266231
- 1795254166 | CLAIMED | victor-2 | heartbeat; lease until 1795268566
- 1795255470 | CLAIMED | victor-2 | heartbeat; lease until 1795269870
- 1795256780 | CLAIMED | victor-2 | heartbeat; lease until 1795271180
- 1795258081 | CLAIMED | victor-2 | heartbeat; lease until 1795272481
- 1795260438 | CLAIMED | victor-2 | heartbeat; lease until 1795274838
- 1795261680 | CLAIMED | victor-2 | heartbeat; lease until 1795276080
- 1795264119 | CLAIMED | victor-2 | heartbeat; lease until 1795278519
- 1795265420 | CLAIMED | victor-2 | heartbeat; lease until 1795279820
- 1795266727 | CLAIMED | victor-2 | heartbeat; lease until 1795281127
- 1795268122 | CLAIMED | victor-2 | heartbeat; lease until 1795282522
- 1795269437 | CLAIMED | victor-2 | heartbeat; lease until 1795283837
- 1795272414 | CLAIMED | victor-2 | heartbeat; lease until 1795286814
- 1795273735 | CLAIMED | victor-2 | heartbeat; lease until 1795288135
- 1795275158 | CLAIMED | victor-2 | heartbeat; lease until 1795289558
- 1795277410 | CLAIMED | victor-2 | heartbeat; lease until 1795291810
- 1795278673 | CLAIMED | victor-2 | heartbeat; lease until 1795293073
- 1795280090 | CLAIMED | victor-2 | heartbeat; lease until 1795294490
- 1795281667 | CLAIMED | victor-2 | heartbeat; lease until 1795296067
- 1795282126 | REVIEW | victor-2 | done; PR https://github.com/crisMmolina/UpiixSol/pull/174; evidence: bash .uak/bin/q bash -c 'npm --prefix web run lint && npm --prefix web run build && uv run pytest -q e2e/test_mail_templates.py e2e/test_mail_composer.py' exit 0 (34 passed); smoke exit 0; all 11 Tests names green at 1280 and 390; design-critic SHIP 51ddfc9 · red at ec85f41: FAILED e2e/test_mail_templates.py::test_gallery_shows_builtins_saved_and_blank_with_thumbnails[desktop]; reviewer: -
- 1795282140 | REVIEW | victor-2 | checkpoint; next: Wait for review of SHA 299cf209; human to amend Paths with Composer.tsx
- 1795282817 | REVIEW | victor-3 | review; approve; SHA 299cf2099f200250d6acfc2be13f705e5e67f8ec; reviewer victor-3
- 1795283074 | REVIEW | victor-2 | heartbeat; lease until 1795369474
- 1795283376 | REVIEW | victor-2 | done; PR https://github.com/crisMmolina/UpiixSol/pull/174; evidence: bash .uak/bin/q bash -c 'npm --prefix web run lint && npm --prefix web run build && uv run pytest -q e2e/test_mail_templates.py e2e/test_mail_composer.py e2e/test_mail_canvas.py' exit 0 (54 passed); design-critic SHIP 99e432b; shots 1280 and 390 · red at ec85f41: FAILED e2e/test_mail_templates.py::test_gallery_shows_builtins_saved_and_blank_with_thumbnails[desktop]; reviewer: -
- 1795283576 | REVIEW | victor-3 | review; approve; SHA 99e432b886c0a1b5b31f8299f6f4c7b02dc426c7; reviewer victor-3
- 1795284098 | REVIEW | victor-2 | done; PR https://github.com/crisMmolina/UpiixSol/pull/174; evidence: bash .uak/bin/q bash -c 'npm --prefix web run lint && npm --prefix web run build && uv run pytest -q e2e/test_mail_templates.py e2e/test_mail_composer.py' exit 0 (34 passed); design-critic SHIP 747fdd6 (a662204 only changes an e2e shot); shots 1280 and 390 · red at ec85f41: FAILED e2e/test_mail_templates.py::test_gallery_shows_builtins_saved_and_blank_with_thumbnails[desktop]; reviewer: -
- 1795284847 | REVIEW | victor-3 | review; approve; SHA a662204a6272805ab1336a5892e75d6ae9288d58; reviewer victor-3
- 1795286175 | INTEGRATED | victor-2 | integrate; recorded by victor-2; PR https://github.com/crisMmolina/UpiixSol/pull/174; merged 1f35f8c6a588e69d84f4c2dbffa269a8ce7a70a9; proof ancestry
