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

Run on 2026-10-08 on branch `feat/ups-029` (main `52286d9`, redesign v2): **12 passed** (6 steps × 2 viewports).
Selectors go by role and accessible name, never by CSS class.

| # | Step | What the test checks | Desktop | Mobile |
|---|---|---|---|---|
| 1 | Register and campus home | Registers with "Crear cuenta" (name, boleta, email, password, privacy notice) and lands on `/`, which shows the "Entrar a UpiixIA" club card. | ✅ | ✅ |
| 2 | Club re-theme + continue | Logs in as `alumno.demo` and opens UpiixIA. The accent changes (campus orange → `#7ED957`) and the top bar shows the UpiixIA logo. The v2 shell is there: the "Principal" icon rail on desktop or the "Principal móvil" tab bar on phones, plus the "Notificaciones" bell. "Continúa aprendiendo" shows the route tile "Continuar: Fundamentos de IA con Python" at 50 %. | ✅ | ✅ |
| 3 | Player + complete | The route tile opens the next lesson (`/a/upiixia/clases/<id>`). A YouTube "ended" message from another origin changes nothing. The same message from `https://www.youtube-nocookie.com`, with the player iframe as source, shows "Clase completada" (no network to YouTube). After a reload the route bar reads 75 % (on mobile it is inside the "Contenido" drawer). | ✅ | ✅ |
| 4 | Community post with image | Posts text and an image in `#upiixia`. The post shows its `/media/` image and also appears in Feed. | ✅ | ✅ |
| 5 | Club admin | `admin.ia` adds a module and a lesson (YouTube, markdown, 2 links) and sets the accent to `#FFB400`. The lesson then shows in the player sidebar and the club uses the new accent. | ✅ | ✅ |
| 6 | Superadmin + new club admin | Creates the club "UpiixRobótica" with "Nuevo club" (logo, accent), creates its admin with a temporary password and publishes a global event. The event shows in `/calendario`, the club card on `/`, and the `#upiixrobotica` channel in Community. The new admin then signs in with the temporary password. There is no banner; the bell reads "Notificaciones (1 sin leer)", its panel says "Cambia tu contraseña provisional", and "Ir a Seguridad" opens `/cuenta?tab=seguridad`. | ✅ | ✅ |

Screenshots per viewport: `1-home`, `2-academy-home`, `3-player`, `4-community`, `5-panel`, `6-calendar`,
`6-home-community` and `6-provisional-password`.

## Notes

- 2026-10-07: `/comunidad` scrolled 61 px sideways at 390 px; fixed in PR #20.
- 2026-10-08: with a freshly built `web/dist`, steps 2, 3 and 6 failed on `main` after the v2 screens landed; fixed in PR #43 (step 6) and PR #45 (steps 2–3). Always build before running the flow: an old `web/dist` hides these failures.
- Steps 2–6 use the seeded demo accounts with the documented seed password. The server runs with `REQUIRE_PASSWORD_CHANGE=false` (UPS-020) and `RATELIMIT_ENABLED=false`, because the flow logs in several times a minute.
- The YouTube video itself never loads in the test: step 3 plays the embed's "ended" message, so the run works offline (Plan B in IDEA §4).
