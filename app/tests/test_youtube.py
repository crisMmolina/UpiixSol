import unittest

import pytest

from app.services.youtube import embed_url, extract_video_id, parse_start, thumbnail_url

VIDEO_ID = "dQw4w9WgXcQ"


class ExtractVideoIdTest(unittest.TestCase):
    def test_accepts_known_url_formats(self) -> None:
        urls = [
            f"https://www.youtube.com/watch?v={VIDEO_ID}",
            f"https://youtube.com/watch?v={VIDEO_ID}&t=42s",
            f"https://m.youtube.com/watch?feature=share&v={VIDEO_ID}",
            f"https://youtu.be/{VIDEO_ID}",
            f"https://youtu.be/{VIDEO_ID}?si=abc123",
            f"https://www.youtube.com/shorts/{VIDEO_ID}",
            f"https://www.youtube.com/embed/{VIDEO_ID}",
            f"https://www.youtube-nocookie.com/embed/{VIDEO_ID}?rel=0",
            f"https://www.youtube.com/live/{VIDEO_ID}",
            f"  http://www.youtube.com/watch?v={VIDEO_ID}  ",
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(extract_video_id(url), VIDEO_ID)

    def test_rejects_invalid_urls(self) -> None:
        urls = [
            "",
            "not a url",
            f"javascript:alert('{VIDEO_ID}')",
            f"https://evil.com/watch?v={VIDEO_ID}",
            f"https://youtube.com.evil.com/watch?v={VIDEO_ID}",
            f"https://evil.com/?u=https://youtu.be/{VIDEO_ID}",
            "https://www.youtube.com/watch?v=short",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ<script>",
            "https://www.youtube.com/watch",
            "https://youtu.be/",
            f"ftp://youtu.be/{VIDEO_ID}",
            f"https://user@youtu.be/{VIDEO_ID}",
            f"https://[::1/watch?v={VIDEO_ID}",
            f"https://www.youtube.com/watch?v={VIDEO_ID}&v={VIDEO_ID}",
            f"https://www.youtube.com/embed/{VIDEO_ID}/extra",
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertIsNone(extract_video_id(url))

    def test_rejects_non_string(self) -> None:
        self.assertIsNone(extract_video_id(None))  # type: ignore[arg-type]


class UrlBuildersTest(unittest.TestCase):
    def test_embed_url_uses_privacy_enhanced_domain(self) -> None:
        self.assertEqual(embed_url(VIDEO_ID), f"https://www.youtube-nocookie.com/embed/{VIDEO_ID}")

    def test_thumbnail_url(self) -> None:
        self.assertEqual(thumbnail_url(VIDEO_ID), f"https://img.youtube.com/vi/{VIDEO_ID}/hqdefault.jpg")

    def test_builders_reject_invalid_id(self) -> None:
        for builder in (embed_url, thumbnail_url):
            with self.subTest(builder=builder.__name__), self.assertRaises(ValueError):
                builder("../../etc")


if __name__ == "__main__":
    unittest.main()


# ── Segments (UPS-045) ───────────────────────────────────────

BASE = f"https://www.youtube.com/watch?v={VIDEO_ID}"


@pytest.mark.parametrize(
    ("url", "seconds"),
    [
        (f"{BASE}&t=850", 850),
        (f"{BASE}&t=850s", 850),
        (f"{BASE}&t=14m10s", 850),
        (f"{BASE}&t=1h2m3s", 3723),
        (f"{BASE}&t=2m", 120),
        (f"{BASE}&start=850", 850),
        (f"https://youtu.be/{VIDEO_ID}?t=90", 90),
        (f"https://youtu.be/{VIDEO_ID}?si=abc&t=0", 0),
        (f"{BASE}#t=14m10s", 850),
        (f"https://www.youtube.com/embed/{VIDEO_ID}?start=42", 42),
    ],
)
def test_parse_start_formats(url: str, seconds: int) -> None:
    assert parse_start(url) == seconds


@pytest.mark.parametrize(
    "url",
    [
        BASE,
        f"{BASE}&t=",
        f"{BASE}&t=abc",
        f"{BASE}&t=-5",
        f"{BASE}&t=1.5",
        f"{BASE}&t=10m99x",
        f"{BASE}&t=javascript:alert(1)",
        f"{BASE}&t=1%26autoplay%3D1",
        f"{BASE}&t=1&t=2",
        f"{BASE}&t=" + "9" * 40,
        f"{BASE}&t=999999",
        "not a url",
        None,
        12,
    ],
)
def test_parse_start_rejects_hostile(url) -> None:
    assert parse_start(url) is None


def test_embed_url_with_segment() -> None:
    assert (
        embed_url(VIDEO_ID, 850, 1500)
        == f"https://www.youtube-nocookie.com/embed/{VIDEO_ID}?start=850&end=1500"
    )
    assert embed_url(VIDEO_ID, None, 60) == f"https://www.youtube-nocookie.com/embed/{VIDEO_ID}?end=60"
    assert embed_url(VIDEO_ID, 30) == f"https://www.youtube-nocookie.com/embed/{VIDEO_ID}?start=30"
    with pytest.raises(ValueError):
        embed_url(VIDEO_ID, "1&autoplay=1")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        embed_url(VIDEO_ID, True)  # type: ignore[arg-type]


def test_embed_url_without_segment_unchanged() -> None:
    assert embed_url(VIDEO_ID) == f"https://www.youtube-nocookie.com/embed/{VIDEO_ID}"
    assert embed_url(VIDEO_ID, None, None) == f"https://www.youtube-nocookie.com/embed/{VIDEO_ID}"
