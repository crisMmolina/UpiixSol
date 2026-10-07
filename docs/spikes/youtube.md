# Spike · YouTube in lessons (UPS-003)

Result: **viable with no API key**. Module `app/services/youtube.py` (stdlib only), tests in `app/tests/test_youtube.py`.

## Accepted formats
| Format | Example |
|---|---|
| watch | `https://www.youtube.com/watch?v=ID` (also `m.`, `music.`, with `&t=`, `&feature=`) |
| short link | `https://youtu.be/ID` (with `?si=`) |
| shorts | `https://www.youtube.com/shorts/ID` |
| embed | `https://www.youtube.com/embed/ID`, `https://www.youtube-nocookie.com/embed/ID` |
| live | `https://www.youtube.com/live/ID` |

The ID must match `[A-Za-z0-9_-]{11}`. Rejected: other domains (including `youtube.com.evil.com`), any scheme other than `http(s)`, URLs with credentials (`user@`), a repeated `v`, and extra path segments.

## How it is used
- Saving a lesson (UPS-008): `extract_video_id(url)` → `None` ⇒ 422 "URL de YouTube no válida". Store `youtube_url` and `youtube_video_id`.
- Player (UPS-007): `embed_url(id)` → `https://www.youtube-nocookie.com/embed/{id}` (privacy-enhanced mode). Thumbnail: `thumbnail_url(id)` → `https://img.youtube.com/vi/{id}/hqdefault.jpg`.
- The server **never** fetches the URL (no SSRF); it only parses it.

## Fallback ("Video no disponible")
- The iframe has no reliable `onerror`. The player shows the thumbnail (or a local placeholder if the thumbnail fails) as the background of the 16:9 box and the iframe on top; if `navigator.onLine === false` or the iframe does not fire `load` within 8 s, it shows "Video no disponible sin conexión" over the thumbnail, keeping the layout.
- Demo lessons can carry a local thumbnail in `media/` (IDEA §4 Plan B).
- Duration: entered by hand by the admin (`duration_min`); YouTube Data API v3 is out of scope for v1.

## References (unverified as of 2026-10-06; check before citing)
- IFrame Player API: https://developers.google.com/youtube/iframe_api_reference
- Privacy-enhanced mode: https://support.google.com/youtube/answer/171780
