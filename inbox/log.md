# Agent messages

Append-only; use bash .uak/bin/uak msg / inbox. Format: - N | epoch | from | to | kind | task | text

- 1 | 1791337639 | claude-a | all | review | UPS-003 | UPS-003 ready for review: https://github.com/crisMmolina/UpiixSol/pull/3 (SHA ca48bc68998a51289528db28016236e44b01cad0). First free agent: /uak-review UPS-003
- 2 | 1791337646 | claude-a | task:UPS-007 | contract | UPS-003 | app/services/youtube.py ready in PR #3 (ca48bc6): extract_video_id(url)->str/None, embed_url(id), thumbnail_url(id); invalid -> 422 on save
- 3 | 1791337646 | claude-a | task:UPS-008 | contract | UPS-003 | app/services/youtube.py ready in PR #3 (ca48bc6): extract_video_id(url)->str/None, embed_url(id), thumbnail_url(id); invalid -> 422 on save
