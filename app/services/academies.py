"""Campus home and academy home (flow step 2). Every number comes from the database (IDEA §5).

Feature-local response models live here; shared contracts stay in app/schemas (owner UPS-002).
"""

from collections import Counter
from collections.abc import Sequence

from pydantic import ConfigDict, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.errors import AppError
from app.models import (
    Academy,
    Channel,
    ChannelType,
    Comment,
    Enrollment,
    Event,
    HomeContent,
    LearningRoute,
    Post,
    Project,
    ProjectStatus,
    Reaction,
    Resource,
    Role,
    User,
)
from app.models.common import utcnow
from app.schemas.academies import AcademyCardOut, AcademyOut, ContinueOut, HomeContentOut
from app.schemas.common import OutModel
from app.schemas.community import PostOut
from app.schemas.content import EventOut, ResourceOut
from app.schemas.learning import RouteCardOut, RouteProgressOut
from app.schemas.users import PublicUser
from app.services.progress import academy_continue, routes_progress

HOME_ACADEMIES = 12
HOME_EVENTS = 5
HOME_POSTS = 5
ACADEMY_RESOURCES = 4


class ProjectCardOut(OutModel):
    id: int
    title: str
    slug: str
    summary: str
    cover_url: str | None


class HomeOut(OutModel):
    hero: HomeContentOut | None
    academies: list[AcademyCardOut]
    featured_projects: list[ProjectCardOut]
    upcoming_events: list[EventOut]
    recent_activity: list[PostOut]


class AcademyHomeOut(OutModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, serialize_by_alias=True)

    academy: AcademyOut
    is_enrolled: bool
    continue_: ContinueOut | None = Field(default=None, alias="continue")  # `continue` is a keyword
    routes: list[RouteCardOut]
    recent_resources: list[ResourceOut]
    latest_posts: list[PostOut]
    upcoming_events: list[EventOut]


class EnrollOut(OutModel):
    enrolled: bool


def get_academy(db: Session, slug: str, user: User | None) -> Academy:
    academy = db.scalar(select(Academy).where(Academy.slug == slug))
    can_see_inactive = user is not None and user.role == Role.superadmin
    if academy is None or (not academy.is_active and not can_see_inactive):
        raise AppError(404, "No encontramos esa academia.")
    return academy


def enrolled_ids(db: Session, user: User | None) -> set[int]:
    if user is None:
        return set()
    return set(db.scalars(select(Enrollment.academy_id).where(Enrollment.user_id == user.id)))


def academy_out(academy: Academy, enrolled: set[int]) -> AcademyOut:
    return AcademyOut.model_validate(academy).model_copy(update={"is_enrolled": academy.id in enrolled})


def card(academy: Academy, enrolled: set[int]) -> AcademyCardOut:
    return AcademyCardOut.model_validate(academy).model_copy(update={"is_enrolled": academy.id in enrolled})


def active_academies_stmt():
    return select(Academy).where(Academy.is_active.is_(True))


def upcoming_events(db: Session, academy_id: int | None = None, limit: int = HOME_EVENTS) -> list[EventOut]:
    stmt = (
        select(Event, Academy.slug)
        .outerjoin(Academy, Academy.id == Event.academy_id)
        .where(Event.ends_at >= utcnow(), or_(Event.academy_id.is_(None), Academy.is_active.is_(True)))
    )
    if academy_id is not None:
        stmt = stmt.where(or_(Event.academy_id == academy_id, Event.academy_id.is_(None)))
    rows = db.execute(stmt.order_by(Event.starts_at, Event.id).limit(limit))
    return [EventOut.model_validate(ev).model_copy(update={"academy_slug": slug}) for ev, slug in rows]


def posts_out(db: Session, posts: Sequence[Post]) -> list[PostOut]:
    """PostOut with author (nickname/avatar only), channel slug, comment and reaction counts: 3 queries."""
    if not posts:
        return []
    post_ids = [p.id for p in posts]
    comments = dict(
        db.execute(
            select(Comment.post_id, func.count())
            .where(Comment.post_id.in_(post_ids), Comment.is_hidden.is_(False))
            .group_by(Comment.post_id)
        ).all()
    )
    reactions: dict[int, Counter] = {}
    for post_id, kind, total in db.execute(
        select(Reaction.post_id, Reaction.kind, func.count())
        .where(Reaction.post_id.in_(post_ids))
        .group_by(Reaction.post_id, Reaction.kind)
    ):
        reactions.setdefault(post_id, Counter())[kind] = total
    slugs = dict(
        db.execute(
            select(Channel.id, Channel.slug).where(Channel.id.in_({p.channel_id for p in posts}))
        ).all()
    )
    return [
        PostOut(
            id=p.id,
            channel_id=p.channel_id,
            channel_slug=slugs.get(p.channel_id),
            author=PublicUser.model_validate(p.author),
            body=p.body,
            image_url=p.image_url,
            link_url=p.link_url,
            created_at=p.created_at,
            comment_count=comments.get(p.id, 0),
            reactions=dict(reactions.get(p.id, {})),
        )
        for p in posts
    ]


def _visible_posts(db: Session, channel_ids: Sequence[int] | None, limit: int) -> list[Post]:
    stmt = select(Post).options(selectinload(Post.author)).where(Post.is_hidden.is_(False))
    if channel_ids is not None:
        stmt = stmt.where(Post.channel_id.in_(channel_ids))
    else:  # campus activity: General + channels of active academies
        visible = (
            select(Channel.id)
            .outerjoin(Academy, Academy.id == Channel.academy_id)
            .where(or_(Channel.type == ChannelType.general, Academy.is_active.is_(True)))
        )
        stmt = stmt.where(Post.channel_id.in_(visible))
    return list(db.scalars(stmt.order_by(Post.created_at.desc(), Post.id.desc()).limit(limit)))


def campus_home(db: Session, user: User) -> HomeOut:
    content = db.get(HomeContent, 1)
    enrolled = enrolled_ids(db, user)
    academies = db.scalars(
        active_academies_stmt().order_by(Academy.position, Academy.id).limit(HOME_ACADEMIES)
    )
    projects: list[Project] = []
    if content and content.featured_project_ids:
        by_id = {
            p.id: p
            for p in db.scalars(
                select(Project).where(
                    Project.id.in_(content.featured_project_ids), Project.status == ProjectStatus.published
                )
            )
        }
        projects = [by_id[i] for i in content.featured_project_ids if i in by_id]
    return HomeOut(
        hero=HomeContentOut.model_validate(content) if content else None,
        academies=[card(a, enrolled) for a in academies],
        featured_projects=[ProjectCardOut.model_validate(p) for p in projects],
        upcoming_events=upcoming_events(db),
        recent_activity=posts_out(db, _visible_posts(db, None, HOME_POSTS)),
    )


def academy_home(db: Session, academy: Academy, user: User) -> dict:
    enrolled = enrolled_ids(db, user)
    routes = list(
        db.scalars(
            select(LearningRoute)
            .where(LearningRoute.academy_id == academy.id, LearningRoute.is_published.is_(True))
            .order_by(LearningRoute.position, LearningRoute.id)
        )
    )
    progress = routes_progress(db, user.id, [r.id for r in routes])
    route_cards = [
        RouteCardOut.model_validate(r).model_copy(
            update={"progress": RouteProgressOut(**progress[r.id].__dict__)}
        )
        for r in routes
    ]
    info = academy_continue(db, user.id, academy.id)
    resources = db.scalars(
        select(Resource)
        .where(Resource.academy_id == academy.id)
        .order_by(Resource.created_at.desc(), Resource.id.desc())
        .limit(ACADEMY_RESOURCES)
    )
    channel_ids = list(db.scalars(select(Channel.id).where(Channel.academy_id == academy.id)))
    return {
        "academy": academy_out(academy, enrolled),
        "is_enrolled": academy.id in enrolled,
        "continue": ContinueOut(**info.__dict__) if info else None,
        "routes": route_cards,
        "recent_resources": [ResourceOut.model_validate(r) for r in resources],
        "latest_posts": posts_out(db, _visible_posts(db, channel_ids, HOME_POSTS)),
        "upcoming_events": upcoming_events(db, academy.id),
    }


def set_enrollment(db: Session, academy: Academy, user: User, enrolled: bool) -> EnrollOut:
    existing = db.get(Enrollment, (user.id, academy.id))
    if enrolled and existing is None:
        db.add(Enrollment(user_id=user.id, academy_id=academy.id))
    elif not enrolled and existing is not None:
        db.delete(existing)
    db.flush()
    return EnrollOut(enrolled=enrolled)
