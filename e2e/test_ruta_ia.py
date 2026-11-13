"""Route "De cero a LLMs" (UPS-047) in a real browser: a member opens lesson 1.2 "Variables", the embed plays
only its segment (start=2938&end=5665) and a simulated `ended` moves the route's progress bar.

The route is seeded on request (`python -m app.seed --ruta-ia`, human decision 2026-11-13), so this module
starts its own server; the shared e2e server keeps the single demo route.
"""

import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from urllib.parse import parse_qs, urlsplit

import pytest
from playwright.sync_api import Browser, Page, expect

from e2e.conftest import ARTIFACTS, ROOT, SEED_PASSWORD, _free_port, _wait_ready
from e2e.test_flow import MEMBER, VIDEO_ENDED

ROUTE = "De cero a LLMs"


@pytest.fixture(scope="module")
def server() -> Iterator[str]:
    workdir = tempfile.TemporaryDirectory(prefix="upiixsol-e2e-ruta-", ignore_cleanup_errors=True)
    env = {
        **os.environ,
        "ENV": "dev",
        "DATABASE_URL": f"sqlite:///{workdir.name}/e2e.db",
        "MEDIA_DIR": f"{workdir.name}/media",
        "COOKIE_SECURE": "false",
        "RATELIMIT_ENABLED": "false",
        "REQUIRE_PASSWORD_CHANGE": "false",
    }
    for command in (["alembic", "upgrade", "head"], ["app.seed", "--ruta-ia"]):
        subprocess.run([sys.executable, "-m", *command], cwd=ROOT, env=env, check=True, capture_output=True)  # noqa: S603
    port = _free_port()
    process = subprocess.Popen(  # noqa: S603
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        _wait_ready(url, process)
        yield url
    finally:
        process.terminate()
        process.wait(timeout=10)
        workdir.cleanup()


def member_page(browser: Browser, server: str) -> Page:
    context = browser.new_context(
        viewport={"width": 1280, "height": 800}, reduced_motion="reduce", locale="es-MX"
    )
    context.set_default_timeout(10_000)
    page = context.new_page()
    page.route(
        "**/www.youtube-nocookie.com/**",
        lambda route: route.fulfill(
            status=200, content_type="text/html", body="<!doctype html><title>video</title>"
        ),
    )
    page.goto(f"{server}/login?next=/a/upiixia/rutas")
    page.get_by_role("textbox", name="Boleta o correo", exact=True).fill(MEMBER)
    page.get_by_label("Contraseña", exact=True).fill(SEED_PASSWORD)
    page.get_by_role("button", name="Entrar").click()
    expect(page).to_have_url(re.compile(r"/a/upiixia/rutas"))
    return page


def test_variables_plays_its_segment_and_completes(browser: Browser, server: str) -> None:
    page = member_page(browser, server)
    try:
        page.get_by_role("link", name=re.compile(ROUTE)).first.click()
        expect(page).to_have_url(re.compile(r"/a/upiixia/clases/\d+"))
        nav = page.locator("aside").get_by_role("navigation", name="Contenido de la ruta")
        nav.get_by_role("link", name=re.compile(r"^Variables")).click()
        expect(page.get_by_role("heading", level=1)).to_have_text("Variables")

        frame = page.locator('iframe[src*="youtube-nocookie.com/embed/Kp4Mvapo5kc"]')
        frame.wait_for(state="attached")
        query = parse_qs(urlsplit(frame.get_attribute("src") or "").query)
        assert (query["start"], query["end"], query["enablejsapi"]) == (["2938"], ["5665"], ["1"])  # noqa: S101
        expect(page.get_by_text("Video en español").first).to_be_visible()

        bar = nav.get_by_role("progressbar")
        before = int(bar.get_attribute("aria-valuenow") or "0")
        page.evaluate(VIDEO_ENDED)
        expect(page.get_by_text("Clase completada").first).to_be_visible()
        expect(bar).not_to_have_attribute("aria-valuenow", str(before))
        assert int(bar.get_attribute("aria-valuenow") or "0") > before  # noqa: S101
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=ARTIFACTS / "ruta-ia-variables.png", full_page=True)
    finally:
        page.context.close()
