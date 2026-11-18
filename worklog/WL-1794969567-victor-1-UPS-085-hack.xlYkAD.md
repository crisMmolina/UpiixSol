# worklog/WL-1794969567-victor-1-UPS-085-hack.xlYkAD.md · UPS-085

## Live summary
- Done: blocks union, migration 0010, MailMessage attachments/reply_to/from_name, Mailgun sender_from, web types
- Decision: batch_alter_table for SQLite FK/unique; MX tz fixed UTC-6
- Why: SQLite cannot ALTER constraints
- Failing: none
- Commands: Verify from TASKS.md; bash .uak/bin/smoke
- Next: Integrated in main: 14598ee685631b15a2c24929b9e359e318c41811 (recorded by victor-1)

## History
- 1794969567 | CLAIMED | victor-1 | claim; next: stubs for the Tests names and `uak red UPS-085`; then the block models, then the migration, then the transport.
- 1794969594 | CLAIMED | victor-1 | heartbeat; lease until 1794983994
- 1794970097 | REVIEW | victor-1 | done; PR https://github.com/crisMmolina/UpiixSol/pull/139; evidence: Verify (blocks+mailgun+contract pytest, alembic up/down on temp sqlite, web build) exit 0; smoke PRODUCT_PASS exit 0; all acceptance criteria met · red at 06b4179: FAILED app/tests/test_mail_blocks.py::test_blocks_accept_each_kind - Attribut...; reviewer: -
- 1794970108 | REVIEW | victor-1 | checkpoint; next: Wait for review of PR 139
- 1794970544 | REVIEW | victor-2 | review; approve; SHA e3148c007eb895f8bd827b4d15f6f8b4178652ad; reviewer victor-2
- 1794970919 | REVIEW | victor-1 | merge rechazado; Shared resource/CI needs a human: app/migrations/versions/0010_mail_blocks.py
- 1794970981 | INTEGRATED | victor-1 | integrate; recorded by victor-1; PR https://github.com/crisMmolina/UpiixSol/pull/139; merged 14598ee685631b15a2c24929b9e359e318c41811; proof ancestry
