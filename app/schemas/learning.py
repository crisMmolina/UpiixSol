from datetime import datetime

from pydantic import Field

from app.schemas.common import HttpUrl, InModel, MarkdownText, OutModel, Title


class LessonLinkIn(InModel):
    label: Title
    url: HttpUrl


class LessonLinkOut(OutModel):
    id: int
    label: str
    url: str


class LessonSummaryOut(OutModel):
    id: int
    title: str
    duration_min: int | None
    position: int
    is_published: bool
    completed: bool = False


class ModuleOut(OutModel):
    id: int
    title: str
    position: int
    completed: int = 0
    total: int = 0
    lessons: list[LessonSummaryOut] = []


class RouteProgressOut(OutModel):
    completed: int
    total: int
    percent: int
    next_lesson_id: int | None


class RouteCardOut(OutModel):
    id: int
    academy_id: int
    title: str
    description: str
    cover_url: str | None
    position: int
    is_published: bool
    progress: RouteProgressOut | None = None


class RouteDetailOut(RouteCardOut):
    modules: list[ModuleOut] = []


class LessonOut(OutModel):
    id: int
    module_id: int
    route_id: int
    academy_slug: str
    title: str
    youtube_video_id: str
    embed_url: str
    thumbnail_url: str
    description: str
    duration_min: int | None
    is_published: bool
    links: list[LessonLinkOut] = []
    completed: bool = False
    completed_at: datetime | None = None
    prev_lesson_id: int | None = None
    next_lesson_id: int | None = None


class RouteIn(InModel):
    title: Title
    description: MarkdownText = ""
    is_published: bool = False


class RouteUpdateIn(InModel):
    title: Title | None = None
    description: MarkdownText | None = None
    is_published: bool | None = None


class ModuleIn(InModel):
    title: Title


class LessonIn(InModel):
    title: Title
    youtube_url: str = Field(max_length=300)  # validated with app/services/youtube.py → 422
    description: MarkdownText = ""
    duration_min: int | None = Field(default=None, ge=1, le=600)
    is_published: bool = False
    links: list[LessonLinkIn] = Field(default_factory=list, max_length=20)


class LessonUpdateIn(InModel):
    title: Title | None = None
    youtube_url: str | None = Field(default=None, max_length=300)
    description: MarkdownText | None = None
    duration_min: int | None = Field(default=None, ge=1, le=600)
    is_published: bool | None = None
    links: list[LessonLinkIn] | None = Field(default=None, max_length=20)
