# worklog/WL-1791507960-joahan-claude-UPS-035-hack.qoPOr1.md · UPS-035

## Live summary
- Done: hidden post images leave /media (moderator copy in media_objects hidden/<key>, both storage modes) + GET /api/posts/{id}/hidden-image; malformed PNG 422; DELETE own posts/comments (+matrix rows, doc regenerated after merging main); club channels: members/admins/superadmins post, can_post flag; community UI: wrapping, synced counters, Ver mas comments, stable channel switch, race-safe posting, FormMessage, animated link/preview/hide, reactions width, shaped skeletons
- Decision: posting in a club channel requires enrollment, its admin or superadmin; General open; reading/comments/reactions open to signed-in users; authors cannot delete hidden posts (audit trail)
- Why: spec 001: member posts in my academy's channel; IDEA 2.1 all clubs visible; membership is self-service (Unirme al club)
- Failing: -
- Commands: ruff check app: ok; pytest --cov app: TOTAL 100%; npm lint: no new warnings in community; npm build: ok; pytest e2e: 39 passed 1 skipped (desktop-only drawer)
- Next: review

## History
- 1791507960 | CLAIMED | joahan-claude | claim; next: security fixes first (hidden image, 500), then layout, then delete.
- 1791510489 | CLAIMED | joahan-claude | heartbeat; lease until 1791524889
- 1791512959 | CLAIMED | joahan-claude | checkpoint; next: review
