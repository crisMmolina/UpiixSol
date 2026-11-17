# worklog/WL-1794943871-victor-2-UPS-075-hack.m1W2sA.md · UPS-075

## Live summary
- Done: template, test send, campaigns, background send, quota, history, matrix
- Decision: Footer links %recipient.unsubscribe_url%; UPS-076 should 303 GET to /baja
- Why: Mailgun only gets name and unsubscribe_url variables
- Failing: none; linked dotenv breaks logo/media matrix rows here (UPS-083), clean checkout green
- Commands: bash .uak/bin/q uv run pytest -q --tb=short -x app/tests/test_mail_template.py app/tests/test_mail_campaigns.py app/tests/test_permissions_matrix.py
- Next: Wait for review of SHA f0bf0f5 (PR 129)

## History
- 1794943871 | CLAIMED | victor-2 | claim; next: stubs for the Tests names and `uak red UPS-075`; then the template, then draft and confirm, then background sending.
- 1794943902 | CLAIMED | victor-2 | heartbeat; lease until 1794958302
- 1794947925 | CLAIMED | victor-2 | heartbeat; lease until 1794962325
- 1794949150 | CLAIMED | victor-2 | heartbeat; lease until 1794963550
- 1794949161 | CLAIMED | victor-2 | pending decision UPS-075-1794949161; option: Footer Darte de baja links to %recipient.unsubscribe_url% (API URL); UPS-076 answers GET /api/mail/unsubscribe?t= with 303 to /baja?t= without changing state; Why: Mailgun only receives name and unsubscribe_url variables (UPS-073), so /baja?t=token cannot be built per recipient in a batch
- 1794949330 | REVIEW | victor-2 | done; PR https://github.com/crisMmolina/UpiixSol/pull/129; evidence: Verify exit 0 in a clean checkout (no dotenv); full suite + ruff green, coverage 99.96%; 16 named tests, matrix rows and docs regenerated · red at f57af16: E   AssertionError: assert '&lt;b&gt;Hola&lt;/b&gt; &amp; bienvenidos' in ''; reviewer: -
- 1794949343 | REVIEW | victor-2 | checkpoint; next: Wait for review of SHA f0bf0f5 (PR 129)
- 1794949638 | REVIEW | victor-1 | review; approve; SHA f0bf0f5f88fb07b17ed5923e6aedf0d62ae01299; reviewer victor-1
- 1794949790 | REVIEW | victor-2 | heartbeat; lease until 1795036190
