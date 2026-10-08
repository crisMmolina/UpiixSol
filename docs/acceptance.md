# Acceptance: demo flow (IDEA §4)

Automated in `e2e/test_flow.py` (UPS-016, updated to the v2 screens by UPS-029). Each run starts its own uvicorn serving the built web, on a freshly
migrated and seeded SQLite DB. The flow runs once per viewport: desktop 1280×800 and mobile 390×844. It uses
reduced motion, locale es-MX and time zone America/Mexico_City.

## How to run it

```bash
uv run pytest -q e2e
```

- The browser is Playwright's Chromium (`uv run playwright install chromium`). If it isn't installed, the run falls back to the local Google Chrome.
- `web/dist` is rebuilt first when it is missing or older than any file in `web/src`, `web/public` or `web/index.html`, so the run never tests a stale build.
- Screenshots go to `e2e/artifacts/<viewport>-<step>.png`, which is git-ignored.
- Every screenshot also checks that the page does not scroll sideways. A failure names the elements that stick out.

## Result

Run on 2026-10-08 on `main` + UPS-029 (redesign v2 merged: UPS-021..024, 026..028): **12 passed** (6 steps × 2 viewports).

| # | Step | What the test checks | Desktop | Mobile |
|---|---|---|---|---|
| 1 | Register and campus home | Registers with "Crear cuenta" (name, boleta, email, password, privacy notice) and lands on `/`, which shows the UpiixIA card. | ✅ | ✅ |
| 2 | Club re-theme + continue | Logs in as `alumno.demo` and opens UpiixIA. The accent changes (campus orange → `#7ED957`), the top bar shows the UpiixIA logo, and the "Continúa aprendiendo" tile "Continuar: Fundamentos de IA con Python" is visible. | ✅ | ✅ |
| 3 | Dark player, completion on video end | The tile resumes at lesson 3 in the dark course view. The test plays the YouTube "ended" message from the `https://www.youtube-nocookie.com` origin with the player iframe as source (a message from another origin changes nothing); the lesson shows "Clase completada" and after a reload the route bar reads 75 % (on mobile inside the "Contenido" drawer). | ✅ | ✅ |
| 4 | Community post with image | Posts text and an image in `#upiixia`. The post shows its `/media/` image and also appears in Feed. | ✅ | ✅ |
| 5 | Club admin | `admin.ia` adds a module and a lesson (YouTube, markdown, 2 links) and sets the accent to `#FFB400`. The lesson then shows in the player sidebar and the club uses the new accent. | ✅ | ✅ |
| 6 | Superadmin | Creates "UpiixRobótica" (logo, accent), creates its admin and publishes a global event. The event shows in `/calendario`, the club card on `/`, and the `#upiixrobotica` channel in Community. | ✅ | ✅ |

## Notes

- Bug found and fixed: `/comunidad` scrolled 61 px sideways at 390 px (PR #20).
- A stale `web/dist` once made the run look green while main was red (2026-10-08); the freshness check above prevents it.
- Steps 2–6 use the seeded demo accounts with the documented seed password. The server runs with `REQUIRE_PASSWORD_CHANGE=false` (UPS-020) and `RATELIMIT_ENABLED=false`, because the flow logs in several times a minute.
- No network to YouTube is needed: completion is driven by the postMessage the embed would send. In a live demo, seek to the end of the video to see the lesson complete; offline (Plan B in IDEA §4) a lesson cannot be completed.
