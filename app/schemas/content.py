from datetime import datetime

from pydantic import Field, model_validator

from app.models.common import ProjectStatus, ResourceType
from app.schemas.common import HttpUrl, InModel, MarkdownText, OutModel, Slug, Title
from app.schemas.users import PublicUser


class ResourceIn(InModel):
    type: ResourceType
    title: Title
    description: MarkdownText = ""
    url: HttpUrl | None = None  # or upload a file → file_url (the router enforces one of the two)


class ResourceOut(OutModel):
    id: int
    academy_id: int
    type: ResourceType
    title: str
    description: str
    url: str | None
    file_url: str | None
    thumbnail_url: str | None
    created_at: datetime


class EventIn(InModel):
    academy_id: int | None = None  # None = global (superadmin only)
    title: Title
    description: MarkdownText = ""
    location: str | None = Field(default=None, max_length=200)
    link: HttpUrl | None = None
    starts_at: datetime
    ends_at: datetime

    @model_validator(mode="after")
    def _ends_after_start(self) -> "EventIn":
        if self.ends_at < self.starts_at:
            raise ValueError("ends_at debe ser posterior a starts_at")
        return self


class EventOut(OutModel):
    id: int
    academy_id: int | None
    academy_slug: str | None = None
    title: str
    description: str
    location: str | None
    link: str | None
    starts_at: datetime
    ends_at: datetime
    cover_url: str | None


class ProjectIn(InModel):
    title: Title
    slug: Slug
    summary: str = Field(default="", max_length=300)
    body: MarkdownText = ""
    authors: str = Field(default="", max_length=300)
    academy_id: int | None = None
    tags: list[str] = Field(default_factory=list, max_length=10)
    status: ProjectStatus = ProjectStatus.draft


class ProjectOut(OutModel):
    id: int
    title: str
    slug: str
    summary: str
    body: str
    cover_url: str | None
    authors: str
    academy_id: int | None
    tags: list[str]
    status: ProjectStatus
    published_at: datetime | None


class BlogPostIn(InModel):
    title: Title
    slug: Slug
    body: MarkdownText = ""
    published: bool = False


class BlogPostOut(OutModel):
    id: int
    title: str
    slug: str
    body: str
    cover_url: str | None
    author: PublicUser | None = None
    published_at: datetime | None
