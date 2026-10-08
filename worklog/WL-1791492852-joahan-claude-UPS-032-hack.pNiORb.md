# worklog/WL-1791492852-joahan-claude-UPS-032-hack.pNiORb.md · UPS-032

## Live summary
- Done: @theme inline color tokens (club + dark palettes reach utilities, club link shades); lib/brand.tsx SITE + Wordmark; wordmark in club header, cards, continue tiles, switcher (unique initials, 44px button, menu inside phone viewport); campus brand from SITE (VITE_SITE_NAME/VITE_SITE_LOGO) + document.title; toasts bottom-right; e2e/test_branding.py
- Decision: -
- Why: -
- Failing: -
- Commands: npm --prefix web run lint: 0 new warnings in touched files; npm --prefix web run build: ok; uv run pytest -q e2e: 14 passed
- Next: review

## History
- 1791492852 | CLAIMED | joahan-claude | claim; next: switch the theme block to `@theme inline`, add the Wordmark, then the brand config.
- 1791493809 | CLAIMED | joahan-claude | checkpoint; next: review
