from datetime import datetime

from pydantic import Field

from app.schemas.common import HexColor, InModel, MarkdownText, OutModel, Slug, Title


class AcademyBranding(OutModel):
    """Feeds the `--academy-*` CSS variables in the web app."""

    slug: str
    name: str
    logo_url: str | None
    mascot_url: str | None
    color_primary: str
    color_secondary: str
    color_accent: str
    color_accent_2: str | None


class AcademyCardOut(AcademyBranding):
    id: int
    short_description: str
    position: int
    is_enrolled: bool = False


class AcademyOut(AcademyCardOut):
    welcome_text: str
    is_active: bool
    created_at: datetime


class AcademyCreateIn(InModel):
    slug: Slug
    name: Title
    short_description: str = Field(default="", max_length=200)
    welcome_text: MarkdownText = ""
    color_primary: HexColor = "#00BF63"
    color_secondary: HexColor = "#04944F"
    color_accent: HexColor = "#F28034"
    color_accent_2: HexColor | None = None
    position: int = 0


class AcademyUpdateIn(InModel):
    name: Title | None = None
    short_description: str | None = Field(default=None, max_length=200)
    welcome_text: MarkdownText | None = None
    color_primary: HexColor | None = None
    color_secondary: HexColor | None = None
    color_accent: HexColor | None = None
    color_accent_2: HexColor | None = None
    position: int | None = None
    is_active: bool | None = None


class BrandingUpdateIn(InModel):
    """What an academy admin may change on their own academy (step 5)."""

    short_description: str | None = Field(default=None, max_length=200)
    welcome_text: MarkdownText | None = None
    color_primary: HexColor | None = None
    color_secondary: HexColor | None = None
    color_accent: HexColor | None = None
    color_accent_2: HexColor | None = None


class ContinueOut(OutModel):
    route_id: int
    lesson_id: int
    lesson_title: str
    lesson_number: int  # 1-based position in the route ("Clase 3")
    percent: int


class HomeContentIn(InModel):
    hero_title: Title
    hero_text: MarkdownText = ""
    highlighted_academy_ids: list[int] = Field(default_factory=list, max_length=20)
    featured_project_ids: list[int] = Field(default_factory=list, max_length=20)


class HomeContentOut(OutModel):
    hero_title: str
    hero_text: str
    highlighted_academy_ids: list[int]
    featured_project_ids: list[int]
