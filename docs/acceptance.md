# Acceptance: demo flow (IDEA §4)

Automated in `e2e/test_flow.py` (UPS-016). Each run starts its own uvicorn serving the built web, on a freshly
migrated and seeded SQLite DB. The flow runs once per viewport: desktop 1280×800 and mobile 390×844. It uses
reduced motion, locale es-MX and time zone America/Mexico_City.

## How to run it

```bash
uv run pytest -q e2e
```

- The browser is Playwright's Chromium (`uv run playwright install chromium`). If it isn't installed, the run falls back to the local Google Chrome.
- If `web/dist` is missing, it is built first (`npm --prefix web run build`).
- Screenshots go to `e2e/artifacts/<viewport>-<step>.png`, which is git-ignored.
- Every screenshot also checks that the page does not scroll sideways. A failure names the elements that stick out.

## Result

Run on 2026-10-07 on branch `feat/ups-016` together with the community fix from PR #20: **12 passed** (6 steps × 2 viewports).

| # | Step | What the test checks | Desktop | Mobile |
|---|---|---|---|---|
| 1 | Register and campus home | Registers with "Crear cuenta" (name, boleta, email, password, privacy notice) and lands on `/`, which shows the UpiixIA card. | ✅ | ✅ |
| 2 | Academy re-theme + continue | Logs in as `alumno.demo` and opens UpiixIA. The accent changes (campus orange → `#7ED957`), the header shows the UpiixIA logo, and "Continuar: Clase 3 · 50 %" is visible. | ✅ | ✅ |
| 3 | Player + complete | "Continuar" opens the player and "Marcar como completada" jumps to the next lesson. After a reload the route bar reads 75 % (on mobile it is inside the "Contenido" drawer). | ✅ | ✅ |
| 4 | Community post with image | Posts text and an image in `#upiixia`. The post shows its `/media/` image and also appears in Feed. | ✅ | ✅ |
| 5 | Academy admin | `admin.ia` adds a module and a lesson (YouTube, markdown, 2 links) and sets the accent to `#FFB400`. The lesson then shows in the player sidebar and the academy uses the new accent. | ✅ | ✅ |
| 6 | Superadmin | Creates "UpiixRobótica" (logo, accent), creates its admin and publishes a global event. The event shows in `/calendario`, the academy card on `/`, and the `#upiixrobotica` channel in Community. | ✅ | ✅ |

## Notes

- Bug found and fixed: `/comunidad` scrolled 61 px sideways at 390 px (PR #20). Until that PR merges, steps 4 and 6 fail at mobile width on `main`.
- Steps 2–6 use the seeded demo accounts with the documented seed password. The server runs with `REQUIRE_PASSWORD_CHANGE=false` (UPS-020) and `RATELIMIT_ENABLED=false`, because the flow logs in several times a minute.
- The YouTube iframe is not asserted. The player is checked through its own controls, so the run works offline (Plan B in IDEA §4).
