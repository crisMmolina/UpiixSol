# Spec 006 · Logos and mascots with a transparent background
- Status: draft, requested by the human (cris) 2026-11-17 · PROJECT principles: 1, 4, 6
- One small feature. No new dependency, no migration.

## Problem
Some uploaded logos and mascots come with an opaque white background (a JPG, or a PNG exported on white). The upload pipeline already keeps real transparency (`RGBA` in, `RGBA` WebP out), so the problem is not the pipeline: the white is part of the picture. On the dark theme, on the colored club header and in emails the logo shows as a white box, and it is useless anywhere that needs a clean cut-out.

## Stories
- As a **superadmin** or **club admin**, I want the white background of a logo or mascot removed when I upload it, so that it sits cleanly on any color.
- As an admin with logos already uploaded, I want to fix the current logo in one click, without hunting for the original file.
- As an admin, I want to see the result on a light and a dark swatch before I am happy with it, and go back if the logo had white on purpose.

## Acceptance criteria (EARS)
- When a `logo` or `mascot` is uploaded with `transparent_background=true`, the system shall make transparent only the near-white pixels (each channel ≥ 245) that are **connected to the image border**, with a soft edge (no white halo), and shall leave every white area enclosed by the artwork opaque (the white inside a letter, an eye or a badge).
- Where the file is a JPG or has no alpha, the system shall convert it to `RGBA` first; a file that already has real transparency is stored as is, and an SVG is never touched.
- If the image has no near-white border (the background is blue, or the white is not at the edge), the system shall store it unchanged and say so ("No encontramos un fondo blanco para quitar.").
- If more than 98 % of the picture would become transparent (a mostly white image), the system shall refuse with 422 and leave the logo unchanged.
- The field is optional and defaults to `false` on the API (existing clients and tests keep their behavior); the upload forms of the club panel and the superadmin brand tab send it checked by default for logo and mascot.
- The same rule applies to the club logo and mascot (`POST /api/academies/{academy_id}/logo|mascot`) and to the site logo and mascot (`POST /api/admin/site/logo|mascot`), with the same permissions as today (superadmin any; club admin only their own club); no new route and no change to the permission matrix.
- While a logo or mascot is already uploaded, the form shall offer "Quitar fondo blanco al logo actual": the browser downloads the current image from `/media/…` and sends it again through the same upload route with the flag on, so no new endpoint exists and the old file is deleted only after the commit, as today.
- The form shall preview the result on a light and a dark swatch (checkerboard behind), and a "Volver a subir el original" path stays available by simply uploading the file again.
- The brand assets in `assets/brand/` and the built-in wordmark are never processed: only user uploads.

## Non-functional
- Pillow only (`ImageDraw.floodfill` on a border-padded mask, `ImageChops`, `GaussianBlur`); the input is already capped at 2 MB and 1024 px, so one call stays under 500 ms for a 1024 px logo.
- No personal data involved; no new log fields.

## Out of scope
- Removing non-white backgrounds, AI cut-outs, color keying, manual erase.
- Processing avatars, covers, post and resource images.
- Re-processing every stored logo in bulk.

## Open questions
1. Should the checkbox be checked by default? Default: yes for logo and mascot, because the request says white backgrounds are the problem. [To validate: cris]
2. A black-text transparent logo vanishes on the dark theme: do we also want a "versión para modo oscuro"? Default: no, out of scope; the dark swatch in the preview makes it visible before saving. [To validate: cris]
