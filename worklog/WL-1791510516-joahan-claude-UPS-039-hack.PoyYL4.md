# worklog/WL-1791510516-joahan-claude-UPS-039-hack.PoyYL4.md · UPS-039

## Live summary
- Done: review fix: LOGO_HEIGHT --logo-h token shared by img and Wordmark in header, card, tile, login, switcher; e2e compares header/card/tile; login same box; home comment cleaned
- Decision: -
- Why: -
- Failing: -
- Commands: web lint no new warnings; web build OK; e2e/test_wordmark.py 6 passed; full e2e 35 passed 1 skipped (pre-existing)
- Next: review

## History
- 1791510516 | CLAIMED | joahan-claude | claim; next: remove the outline, then the brand leftovers, then the flag.
- 1791513481 | CLAIMED | joahan-claude | checkpoint; next: review
- 1791513521 | REVIEW | joahan-claude | done; PR https://github.com/crisMmolina/UpiixSol/pull/new/feat/ups-039; evidence: 7b93197: pytest 100 %, e2e 33 passed 1 skipped (new test_wordmark), ratelimit tests; reviewer: -
- 1791513529 | REVIEW | joahan-claude | pending decision UPS-039-1791513529; option: UPS-039 adds e2e/test_wordmark.py and edits one line of e2e/test_branding.py (case-insensitive name count) outside its Paths; Why: the wordmark now renders lowercase via CSS; browser coverage required
- 1791514198 | REVIEW | joahan-rev | review; reject; SHA 7b93197aa37878ad690e8972d6372e687f93145a; reviewer joahan-rev
- 1791514710 | REVIEW | joahan-claude | checkpoint; next: review
- 1791514744 | REVIEW | joahan-claude | pending decision UPS-039-1791514744; option: UPS-039 also edits web/src/features/home/index.tsx and web/src/layouts/{AcademyLayout,CampusLayout,ClubSwitcher}.tsx (owned by unclaimed UPS-040) so every text wordmark shares the logo height token; Why: product owner: the no-logo wordmark must match the logo size everywhere; UPS-040 is not claimed yet
- 1791515250 | REVIEW | joahan-rev | review; approve; SHA 9a7c788e7e26fe51da2a258837e97a1a7192c76c; reviewer joahan-rev
