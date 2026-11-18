# Plan 006 · Transparent logos

## Design
- `app/services/media.py`: new `remove_white_background(image: Image.Image) -> tuple[Image.Image, bool]` (returns the image and whether anything changed). Steps: `RGBA` copy; near-white mask (each channel ≥ 245); pad the mask by 1 px of white; one `ImageDraw.floodfill` from `(0, 0)` so only white connected to the border is selected; invert; slight `GaussianBlur` on the alpha for the soft edge; reject when the transparent share is over 98 %. `save_image_bytes(data, kind, *, transparent_background=False)` calls it for `logo` and `mascot` only, after `thumbnail` and before the WebP encode; SVG returns early as today.
- `save_upload(file, kind, transparent_background=False)` forwards the flag; the club and site upload services pass it through.
- Routers `app/routers/academy_admin.py` and `app/routers/site.py` take `transparent_background: bool = Form(False)` next to the file. No new route.
- Web: `web/src/features/academy-admin/index.tsx` and `web/src/features/superadmin/SiteBrandTab.tsx` get a checkbox (checked by default for logo and mascot), the light and dark swatch preview with a checkerboard, and the "Quitar fondo blanco al logo actual" button that re-sends the current `/media/…` image through the same route.

## Data and migrations
None. The result is stored like any logo (`/media/logo/<uuid>.webp`, RGBA).

## Contracts
Existing routes gain an optional multipart field `transparent_background` (boolean, default false). Responses are unchanged (`AcademyOut`, `SiteOut`).

## Threat model (STRIDE)
| Threat | Vector | Mitigation | Test |
|---|---|---|---|
| Denial of service | Large or crafted image makes the flood fill slow | input already capped at 2 MB and 1024 px, decompression-bomb guard stays, one fill per upload | removes_white_border_in_under_a_second_on_a_1024px_logo |
| Tampering | Flag used to make an arbitrary image vanish | refuse when more than 98 % becomes transparent; logo and mascot kinds only; same permissions as today | refuses_a_mostly_white_image_with_422 |
| Elevation of privilege | Club admin processes another club's logo | the route and its scope check are unchanged (`academy_for` reads the academy from the DB) | existing matrix rows for the four routes |
| Tampering / XSS | SVG slips through the new path | SVG returns before the raster path, flag ignored | svg_is_never_processed |
| Information disclosure | The button downloads another origin | only same-origin `/media/…` paths are fetched (`safeAssetPath`) | e2e test that checks the request URL |

## Observability
None beyond the access log of the upload route.

## Rollout and rollback
Ships in one deploy, no flag: the default is `false`, so nothing changes until an admin ticks the box. Rollback is redeploying the previous image; images already processed stay as stored.

## Cost
No dependency and no storage change (a transparent WebP is about the same size).

## Tasks
- UPS-095 · Logos and mascots with a transparent background (P1, wave 1, no dependency).
