"""All SQLAlchemy models (contract, owner UPS-002).

Importing this package registers them on Base.metadata.
"""

from app.models.academy import Academy, Enrollment
from app.models.analytics import ActivityEvent
from app.models.common import ChannelType, ProjectStatus, ResourceType, Role
from app.models.community import Channel, Comment, Post, Reaction
from app.models.content import BlogPost, Event, HomeContent, Project, Resource
from app.models.learning import LearningRoute, Lesson, LessonLink, LessonProgress, Module
from app.models.media import MediaObject
from app.models.user import RefreshToken, User

__all__ = [
    "Academy",
    "ActivityEvent",
    "BlogPost",
    "Channel",
    "ChannelType",
    "Comment",
    "Enrollment",
    "Event",
    "HomeContent",
    "LearningRoute",
    "Lesson",
    "LessonLink",
    "LessonProgress",
    "MediaObject",
    "Module",
    "Post",
    "Project",
    "ProjectStatus",
    "Reaction",
    "RefreshToken",
    "Resource",
    "ResourceType",
    "Role",
    "User",
]
