import pytest
from pydantic import ValidationError

from app.sanitize import clean_markdown, safe_url
from app.schemas.academies import BrandingUpdateIn
from app.schemas.learning import LessonLinkIn
from app.schemas.users import RegisterIn


@pytest.mark.parametrize(
    "payload",
    [
        "<script>alert(1)</script>hola",
        '<img src=x onerror="alert(1)">hola',
        '<a href="javascript:alert(1)">hola</a>',
        "<iframe src='https://evil.com'></iframe>hola",
        '<p style="background:url(javascript:alert(1))">hola</p>',
        "<svg onload=alert(1)>hola",
    ],
)
def test_clean_markdown_removes_scripts(payload: str) -> None:
    cleaned = clean_markdown(payload)
    assert "hola" in cleaned
    for bad in ("<script", "onerror", "javascript:", "<iframe", "onload", "style="):
        assert bad not in cleaned.lower()


def test_clean_markdown_keeps_markdown_and_safe_html() -> None:
    text = "# Título\n\n> cita & más\n\n**negritas** y [liga](https://upiixsol.dev)\n\n<strong>ok</strong>"
    cleaned = clean_markdown(text)
    assert "> cita & más" in cleaned
    assert "**negritas**" in cleaned and "<strong>ok</strong>" in cleaned


def test_links_get_safe_rel() -> None:
    assert 'rel="noopener noreferrer nofollow"' in clean_markdown('<a href="https://a.mx">a</a>')


@pytest.mark.parametrize("url", ["https://docs.python.org/3/", "http://upiiz.ipn.mx/x?y=1"])
def test_safe_url_accepts_http(url: str) -> None:
    assert safe_url(f"  {url} ") == url


@pytest.mark.parametrize(
    "url",
    ["javascript:alert(1)", "data:text/html,hi", "/relative", "ftp://x.mx", "https://", "https://a .mx"],
)
def test_safe_url_rejects_others(url: str) -> None:
    with pytest.raises(ValueError):
        safe_url(url)


def test_schemas_validate_urls_colors_and_forbid_extra_fields() -> None:
    with pytest.raises(ValidationError):
        LessonLinkIn(label="x", url="javascript:alert(1)")
    assert BrandingUpdateIn(color_accent="#7ed957").color_accent == "#7ED957"
    with pytest.raises(ValidationError):
        BrandingUpdateIn(color_accent="red")
    with pytest.raises(ValidationError):  # mass assignment: role is not a register field
        RegisterIn(
            full_name="Ana López",
            boleta="2026000001",
            email="a@ipn.mx",
            password="12345678",
            accept_privacy=True,
            role="superadmin",
        )
    with pytest.raises(ValidationError):
        RegisterIn(
            full_name="Ana López", boleta="123", email="a@ipn.mx", password="12345678", accept_privacy=True
        )
    user = RegisterIn(
        full_name="Ana López",
        boleta="2026000001",
        email="Ana@IPN.mx",
        password="12345678",
        accept_privacy=True,
    )
    assert user.email == "ana@ipn.mx"
