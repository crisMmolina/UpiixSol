"""End-to-end fixtures (UPS-016): a real uvicorn serving the built web on a freshly seeded SQLite DB.

The flow runs once per viewport (1280 and 390 wide), each on its own server and database. The browser is
the bundled Playwright Chromium when installed (`uv run playwright install chromium`), otherwise the local
Google Chrome (`channel="chrome"`). Screenshots go to e2e/artifacts/ (git-ignored).
"""

import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from playwright.sync_api import Browser, Page, Playwright, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "e2e" / "artifacts"
SEED_PASSWORD = "admin123"  # noqa: S105 (documented demo seed password, IDEA §2.3)
# Deepest elements sticking out of the viewport (tag.class), to point at the cause of an overflow.
WIDEST = """
  [...document.querySelectorAll('body *')]
    .filter((el) => el.getBoundingClientRect().right > window.innerWidth + 1)
    .filter((el) => ![...el.children].some((c) => c.getBoundingClientRect().right > window.innerWidth + 1))
    .slice(0, 3)
    .map((el) => `${el.tagName.toLowerCase()}.${[...el.classList].slice(0, 4).join('.')}`)
"""
VIEWPORTS = {"desktop": (1280, 800), "mobile": (390, 844)}


@dataclass
class Site:
    base_url: str
    name: str  # desktop | mobile
    page: Page

    def url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def shot(self, step: str) -> None:
        """Screenshot of the step + the layout check: no horizontal page scroll at any viewport."""
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=ARTIFACTS / f"{self.name}-{step}.png", full_page=True)
        overflow = self.page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        if overflow > 0:
            culprits = self.page.evaluate(WIDEST)
            raise AssertionError(f"{self.name}/{step}: page scrolls horizontally by {overflow}px: {culprits}")


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_ready(url: str, server: subprocess.Popen, timeout: float = 30) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if server.poll() is not None:
            raise RuntimeError(f"uvicorn exited with {server.returncode}")
        try:
            with urllib.request.urlopen(f"{url}/api/ready", timeout=1) as response:  # noqa: S310 (localhost)
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.3)
    raise TimeoutError(f"{url} not ready after {timeout}s")


def _dist_is_stale() -> bool:
    """True when web/dist is missing or older than any source file (a stale build hides UI changes)."""
    index = ROOT / "web" / "dist" / "index.html"
    if not index.exists():
        return True
    built = index.stat().st_mtime
    sources = [
        ROOT / "web" / "index.html",
        *(ROOT / "web" / "src").rglob("*"),
        *(ROOT / "web" / "public").rglob("*"),
    ]
    return any(path.is_file() and path.stat().st_mtime > built for path in sources)


@pytest.fixture(scope="session", autouse=True)
def web_build() -> None:
    if _dist_is_stale():
        subprocess.run(["npm", "--prefix", "web", "run", "build"], cwd=ROOT, check=True)  # noqa: S607


def _start_server() -> tuple[str, subprocess.Popen, tempfile.TemporaryDirectory]:
    workdir = tempfile.TemporaryDirectory(prefix="upiixsol-e2e-")
    env = {
        **os.environ,
        "ENV": "dev",
        "DATABASE_URL": f"sqlite:///{workdir.name}/e2e.db",
        "MEDIA_DIR": f"{workdir.name}/media",
        "COOKIE_SECURE": "false",  # plain http on localhost
        "RATELIMIT_ENABLED": "false",  # the flow logs in several times per minute
        "REQUIRE_PASSWORD_CHANGE": "false",  # demo accounts keep the seed password (UPS-020)
    }
    for module in (["alembic", "upgrade", "head"], ["app.seed"]):
        subprocess.run([sys.executable, "-m", *module], cwd=ROOT, env=env, check=True, capture_output=True)  # noqa: S603
    port = _free_port()
    server = subprocess.Popen(  # noqa: S603
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    _wait_ready(url, server)
    return url, server, workdir


@pytest.fixture(scope="session")
def playwright() -> Iterator[Playwright]:
    with sync_playwright() as instance:
        yield instance


@pytest.fixture(scope="session")
def browser(playwright: Playwright) -> Iterator[Browser]:
    try:
        launched = playwright.chromium.launch()
    except Exception:  # bundled Chromium not installed → local Chrome
        launched = playwright.chromium.launch(channel="chrome")
    yield launched
    launched.close()


@pytest.fixture(scope="module", params=list(VIEWPORTS))
def site(request: pytest.FixtureRequest, browser: Browser) -> Iterator[Site]:
    url, server, workdir = _start_server()
    width, height = VIEWPORTS[request.param]
    context = browser.new_context(
        viewport={"width": width, "height": height},
        reduced_motion="reduce",
        locale="es-MX",
        timezone_id="America/Mexico_City",
    )
    context.set_default_timeout(10_000)
    try:
        yield Site(base_url=url, name=request.param, page=context.new_page())
    finally:
        context.close()
        server.terminate()
        server.wait(timeout=10)
        workdir.cleanup()
