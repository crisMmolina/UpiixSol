from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, EmailStr, Field, StringConstraints

from app.models.common import Role
from app.schemas.common import InModel, OutModel

Boleta = Annotated[str, StringConstraints(pattern=r"^\d{10}$")]  # IDEA §2.2 [To validate: exact IPN format]
Password = Annotated[str, StringConstraints(min_length=8, max_length=128)]
Email = Annotated[EmailStr, AfterValidator(str.lower)]
Nickname = Annotated[str, StringConstraints(min_length=2, max_length=40)]
FullName = Annotated[str, StringConstraints(min_length=3, max_length=120)]


class PublicUser(OutModel):
    """The only user shape shown in the community: never email or boleta (IDEA §9 ethics)."""

    id: int
    nickname: str
    avatar_url: str | None = None


class UserMe(OutModel):
    id: int
    role: Role
    email: str
    full_name: str
    nickname: str
    boleta: str | None
    avatar_url: str | None
    academy_id: int | None
    academy_slug: str | None = None
    must_change_password: bool


class UserAdminOut(OutModel):
    """Visible to superadmins (and boleta to the academy admin for their enrollees)."""

    id: int
    role: Role
    email: str
    full_name: str
    nickname: str
    boleta: str | None
    academy_id: int | None
    is_active: bool
    must_change_password: bool
    created_at: datetime


class RegisterIn(InModel):
    full_name: FullName
    boleta: Boleta
    email: Email
    password: Password
    accept_privacy: Literal[True]
    nickname: Nickname | None = None


class LoginIn(InModel):
    email: Email
    password: Annotated[str, StringConstraints(min_length=1, max_length=128)]


class TokenOut(OutModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 (not a secret)
    expires_in: int
    user: UserMe


class ProfileUpdateIn(InModel):
    nickname: Nickname | None = None
    full_name: FullName | None = None


class EmailChangeIn(InModel):
    new_email: Email
    current_password: Annotated[str, StringConstraints(min_length=1, max_length=128)]


class PasswordChangeIn(InModel):
    current_password: Annotated[str, StringConstraints(min_length=1, max_length=128)]
    new_password: Password
    confirm_password: Password


class AdminUserCreateIn(InModel):
    role: Literal[Role.academy_admin, Role.member]
    email: Email
    full_name: FullName
    nickname: Nickname | None = None
    boleta: Boleta | None = None
    academy_id: int | None = Field(default=None, description="Required for academy_admin")
    password: Password


class AdminUserUpdateIn(InModel):
    full_name: FullName | None = None
    nickname: Nickname | None = None
    academy_id: int | None = None
    is_active: bool | None = None


class PasswordResetOut(OutModel):
    temporary_password: str
