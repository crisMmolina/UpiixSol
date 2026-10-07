# PROJECT · UpiixSol Campus (marathon mode)

> The project constitution. Humans change it by reviewed PR. uak reads the last block from the remote `main`.
> Product spec: `IDEA.md`. UI and docs language: Spanish (Mexico).

## Purpose
For members of the UpiixSol student club (IPN · UPIIZ) whose material is scattered across WhatsApp, Drive and Discord: one campus where they enter any academy, resume the lesson where they left off, and talk with their community. Outcome: the 6-step acceptance flow in `IDEA.md` §4 works end to end, on desktop and mobile, for delivery on **Thursday 8 Oct 2026** and for recurring daily use during the semester.

## Non-negotiable principles
1. Secure and private by default: least privilege, permissions enforced in the backend per endpoint (role × academy scope), passwords hashed, boleta/email visible only to the user and superadmins.
2. Nothing reaches `main` without green CI and an approving review from a reviewer that is not the author. The CODEOWNER (@crisMmolina) can audit and revert any merge.
3. Every decision that is costly to reverse has an ADR in `docs/adr/`.
4. No number shown in the UI (progress, counts, dates) comes from an LLM; everything comes from database queries.
5. **No AI authorship in the repo:** commits and PRs never carry `Co-Authored-By` trailers or "Generated with" lines for any AI agent. Commits go out under the human's git identity.
6. Brand assets in `assets/brand/` are used as-is; never redrawn or recreated.

## Non-functional requirements (measurable)
| Attribute | Target | Measured by |
|---|---|---|
| Latency | p95 < 300 ms on `GET /api/academies/{slug}/home` and `GET /api/lessons/{id}` (seeded data) | pytest timing test / local load test |
| Availability | 99.5 % monthly once deployed | uptime monitor on `GET /api/health` (when prod exists) |
| Data | RPO 24 h · RTO 4 h | daily `pg_dump` + rehearsed restore |
| Frontend | < 250 KB gzipped initial JS · LCP < 2.5 s | `vite build` report / Lighthouse |
| Coverage | **target 100 %** on `app/` (domain, services, routers); CI fails below the agreed floor | `pytest --cov=app --cov-report=term-missing` |
| Pagination | no list endpoint returns more than 50 items | tests per list endpoint |
| Security | rate limit 5/min/IP on login/register, 10/min/user on posts; permission matrix §2.1 fully covered | pytest permission-matrix tests |

## Environments and ownership
| Env | URL | Deploys | Secrets in |
|---|---|---|---|
| dev | `http://localhost:$UAK_PORT` (api) · `$UAK_PORT+1` (web) | each agent in its worktree | `.env` (git-ignored) |
| prod | not decided yet (Docker Compose target) | a human, via a semver release | `.env` on the server |

CODEOWNERS: `*` → @crisMmolina · On-call: @crisMmolina · Runbook: `docs/runbook.md`.

## Executable config
```text
Mode: marathon
Backlog-Proposed-Epoch: 0
Backlog-Approved: yes
Autonomy: yes
Auto-Merge: yes
Review-Mode: gh
Plan-Channel: main
Freeze-Epoch: 0
Lease-Seconds: 14400
Review-Lease-Seconds: 86400
Events-Per-Session: 150
Checkpoint-Percent: 60
Merge-Lease-Seconds: 1800
Merge-Wait-Seconds: 180
```
