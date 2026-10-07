"""Project gallery (IDEA §9): public listing and detail of published projects, superadmin CRUD.

Drafts are invisible (404) to everyone but superadmins. `published_at` is set the first time a project
is published and cleared when it goes back to draft.
"""

from fastapi import UploadFile
from sqlalchemy import Select, String, cast, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import Academy, Project, ProjectStatus, Role, User
from app.models.common import utcnow
from app.sanitize import clean_markdown
from app.schemas.content import ProjectIn, ProjectOut
from app.services import media


def _not_found() -> AppError:
    return AppError(404, "No encontramos ese proyecto.")


def is_superadmin(user: User | None) -> bool:
    return user is not None and user.role == Role.superadmin


def list_stmt(tag: str | None, drafts: bool) -> Select:
    stmt = select(Project)
    if not drafts:
        stmt = stmt.where(Project.status == ProjectStatus.published)
    if tag:
        # JSON list column: portable filter on its serialized text (SQLite and Postgres), wildcards escaped.
        stmt = stmt.where(cast(Project.tags, String).contains(f'"{tag.lower()}"', autoescape=True))
    return stmt


def get_by_slug(db: Session, slug: str, user: User | None) -> ProjectOut:
    project = db.scalar(select(Project).where(Project.slug == slug))
    if project is None or (project.status != ProjectStatus.published and not is_superadmin(user)):
        raise _not_found()
    return ProjectOut.model_validate(project)


def get(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise _not_found()
    return project


def _apply(db: Session, project: Project, data: ProjectIn) -> None:
    if data.academy_id is not None and db.get(Academy, data.academy_id) is None:
        raise AppError(422, "Esa academia no existe.", code="invalid_academy")
    project.title = data.title
    project.slug = data.slug
    project.summary = data.summary
    project.body = clean_markdown(data.body)
    project.authors = data.authors
    project.academy_id = data.academy_id
    project.tags = [tag.strip().lower() for tag in data.tags if tag.strip()]
    if data.status == ProjectStatus.published and project.published_at is None:
        project.published_at = utcnow()
    elif data.status == ProjectStatus.draft:
        project.published_at = None
    project.status = data.status


def save(db: Session, project: Project, data: ProjectIn) -> ProjectOut:
    _apply(db, project, data)
    try:
        with db.begin_nested():  # duplicate slug (even concurrent) → 409, never 500
            db.add(project)
            db.flush()
    except IntegrityError as exc:
        raise AppError(409, "Ese identificador (slug) ya está en uso.", code="conflict") from exc
    return ProjectOut.model_validate(project)


async def replace_cover(db: Session, project: Project, file: UploadFile) -> ProjectOut:
    """Store the new cover, commit, and only then delete the previous one (no orphans, no data loss)."""
    url = await media.save_upload(file, "cover")
    previous = project.cover_url
    try:
        project.cover_url = url
        db.commit()
    except Exception:
        db.rollback()
        media.delete_media(url)
        raise
    media.delete_media(previous)
    return ProjectOut.model_validate(project)


def delete(db: Session, project: Project) -> None:
    cover = project.cover_url
    db.delete(project)
    db.commit()
    media.delete_media(cover)
