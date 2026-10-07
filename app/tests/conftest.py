"""Shared fixtures (owner UPS-002): in-memory DB per test, API client and per-role clients.

Each test gets an empty SQLite DB with the full schema. Fixtures `seeded`, `as_superadmin`,
`as_admin_ia`, `as_member` load the demo seed (IDEA §2.3, §3).
"""

import os
import tempfile

os.environ.setdefault("ENV", "test")
os.environ.setdefault("MEDIA_DIR", tempfile.mkdtemp(prefix="upiixsol-media-"))

from collections.abc import Iterator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import Engine, event  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.models  # noqa: E402,F401  (registers every model)
from app.db import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Academy, Role, User  # noqa: E402
from app.ratelimit import limiter  # noqa: E402
from app.security import create_access_token, hash_password  # noqa: E402


@pytest.fixture
def engine() -> Iterator[Engine]:
    from sqlalchemy import create_engine

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def _fks(dbapi_connection, _record) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def _reset_rate_limits() -> Iterator[None]:
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


def make_user(
    db: Session,
    *,
    role: Role = Role.member,
    email: str = "user@upiixsol.dev",
    academy_id: int | None = None,
    boleta: str | None = None,
    password: str = "password123",  # noqa: S107 (test fixture)
    is_active: bool = True,
) -> User:
    user = User(
        role=role,
        email=email,
        password_hash=hash_password(password),
        full_name="Usuario Prueba",
        nickname=email.split("@")[0],
        boleta=boleta,
        academy_id=academy_id,
        is_active=is_active,
    )
    db.add(user)
    db.flush()
    return user


def make_academy(db: Session, slug: str = "upiixia", name: str = "UpiixIA") -> Academy:
    academy = Academy(slug=slug, name=name)
    db.add(academy)
    db.flush()
    return academy


def auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user)}"}


@pytest.fixture
def academy(db: Session) -> Academy:
    return make_academy(db)


@pytest.fixture
def member(db: Session) -> User:
    return make_user(db, email="member@upiixsol.dev", boleta="2026000001")


@pytest.fixture
def seeded(db: Session) -> dict:
    from app.seed import seed

    return seed(db)


def _client_as(db: Session, email: str) -> Iterator[TestClient]:
    user = db.query(User).filter_by(email=email).one()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app, headers=auth_headers(user)) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def as_superadmin(db: Session, seeded: dict) -> Iterator[TestClient]:
    yield from _client_as(db, "superadmin1@upiixsol.dev")


@pytest.fixture
def as_admin_ia(db: Session, seeded: dict) -> Iterator[TestClient]:
    yield from _client_as(db, "admin.ia@upiixsol.dev")


@pytest.fixture
def as_member(db: Session, seeded: dict) -> Iterator[TestClient]:
    yield from _client_as(db, "alumno.demo@upiixsol.dev")
