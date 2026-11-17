# Lessons (uak learn)

Append-only. Format: - N | epoch | agent | task | paths | text. `uak recall` and `uak next` show the ones for your paths.

- 1 | 1794538122 | cris-dev | UPS-061 | web/src/components/Overlay.tsx,e2e/test_overlay_focus.py | e2e/test_mobile.py tab-bar check can flake under the full e2e suite (panel Recursos, 390): passes alone 3/3 · e2e/test_mobile.py UNDER_TAB_BAR/scroll_to_end · wait for the panel list to settle before scrolling, or rerun alone
- 2 | 1794938374 | victor-1 | UPS-072 | app/models/mail.py,app/models/__init__.py,app/migrations/versions/0009_mail.py,app/config.py,.env.example,app/services/mailer.py,app/tests/test_mail_contract.py,web/src/lib/types.ts | alembic env.py fileConfig disables existing loggers · tests calling command.upgrade/downgrade · restore logger.disabled afterwards, see test_mail_contract
