import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Academy, Channel, ChannelType, Post, Reaction
from app.tests.conftest import auth_headers, make_academy, make_user


@pytest.fixture
def post(db: Session, seeded: dict) -> Post:
    return db.scalar(select(Post).where(Post.is_hidden.is_(False)).order_by(Post.id))


def _count(db: Session, post_id: int, kind: str | None = None) -> int:
    stmt = select(func.count()).select_from(Reaction).where(Reaction.post_id == post_id)
    if kind:
        stmt = stmt.where(Reaction.kind == kind)
    return db.scalar(stmt)


def test_reaction_idempotent(as_member: TestClient, post: Post, db: Session) -> None:
    first = as_member.put(f"/api/posts/{post.id}/reactions/fire")
    second = as_member.put(f"/api/posts/{post.id}/reactions/fire")
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert second.json()["post_id"] == post.id
    assert second.json()["reactions"]["fire"] == 1
    assert second.json()["mine"] == ["fire"]
    assert _count(db, post.id, "fire") == 1


def test_one_per_user_and_kind_counts_aggregate(
    as_member: TestClient, as_admin_ia: TestClient, post: Post
) -> None:
    as_member.put(f"/api/posts/{post.id}/reactions/like")
    as_member.put(f"/api/posts/{post.id}/reactions/idea")
    body = as_admin_ia.put(f"/api/posts/{post.id}/reactions/like").json()
    assert body["reactions"] == {"like": 2, "idea": 1}
    assert body["mine"] == ["like"]


def test_delete_is_idempotent(as_member: TestClient, post: Post, db: Session) -> None:
    as_member.put(f"/api/posts/{post.id}/reactions/love")
    first = as_member.delete(f"/api/posts/{post.id}/reactions/love")
    second = as_member.delete(f"/api/posts/{post.id}/reactions/love")
    assert first.status_code == second.status_code == 200
    assert second.json()["mine"] == [] and "love" not in second.json()["reactions"]
    assert _count(db, post.id) == 0


def test_delete_only_removes_own_reaction(as_member: TestClient, as_admin_ia: TestClient, post: Post) -> None:
    as_admin_ia.put(f"/api/posts/{post.id}/reactions/clap")
    body = as_member.delete(f"/api/posts/{post.id}/reactions/clap").json()
    assert body["reactions"] == {"clap": 1}


def test_counts_appear_in_post_listing(as_member: TestClient, post: Post) -> None:
    as_member.put(f"/api/posts/{post.id}/reactions/fire")
    items = as_member.get(f"/api/channels/{post.channel_id}/posts").json()["items"]
    assert next(i for i in items if i["id"] == post.id)["reactions"] == {"fire": 1}


def test_unknown_kind_422(as_member: TestClient, post: Post) -> None:
    for kind in ("poop", "LIKE", "x" * 30):
        assert as_member.put(f"/api/posts/{post.id}/reactions/{kind}").status_code == 422


def test_anonymous_401(client: TestClient, post: Post) -> None:
    assert client.put(f"/api/posts/{post.id}/reactions/like").status_code == 401
    assert client.delete(f"/api/posts/{post.id}/reactions/like").status_code == 401
    assert client.get("/api/reactions/mine", params={"post_ids": str(post.id)}).status_code == 401


def test_missing_or_hidden_post_404(as_member: TestClient, post: Post, db: Session) -> None:
    assert as_member.put("/api/posts/999999/reactions/like").status_code == 404
    post.is_hidden = True
    db.flush()
    assert as_member.put(f"/api/posts/{post.id}/reactions/like").status_code == 404
    assert as_member.delete(f"/api/posts/{post.id}/reactions/like").status_code == 404


def test_post_in_inactive_academy_channel_404(as_member: TestClient, db: Session, seeded: dict) -> None:
    robo: Academy = make_academy(db, "robotica", "UpiixRobótica")
    channel = Channel(type=ChannelType.academy, academy_id=robo.id, name="Robótica", slug="robotica")
    db.add(channel)
    db.flush()
    hidden_post = Post(channel_id=channel.id, author_id=seeded["admin_ia_id"], body="hola")
    db.add(hidden_post)
    robo.is_active = False
    db.flush()
    assert as_member.put(f"/api/posts/{hidden_post.id}/reactions/like").status_code == 404


def test_mine_lists_my_kinds_for_visible_posts(as_member: TestClient, post: Post, db: Session) -> None:
    other = db.scalar(select(Post).where(Post.id != post.id, Post.is_hidden.is_(False)))
    as_member.put(f"/api/posts/{post.id}/reactions/like")
    as_member.put(f"/api/posts/{post.id}/reactions/idea")
    body = as_member.get("/api/reactions/mine", params={"post_ids": f"{post.id},{other.id},999999"}).json()
    assert body == {str(post.id): ["idea", "like"]}


def test_mine_is_per_user(as_member: TestClient, db: Session, post: Post) -> None:
    stranger = make_user(db, email="otro@upiixsol.dev", boleta="2026000099")
    as_member.put(f"/api/posts/{post.id}/reactions/like")
    response = as_member.get(
        "/api/reactions/mine", params={"post_ids": str(post.id)}, headers=auth_headers(stranger)
    )
    assert response.json() == {}


@pytest.mark.parametrize("post_ids", ["", "a,b", ",".join(str(i) for i in range(1, 52)), "1," * 300])
def test_mine_validates_ids_422(as_member: TestClient, post_ids: str) -> None:
    assert as_member.get("/api/reactions/mine", params={"post_ids": post_ids}).status_code == 422


def test_out_of_range_ids_422(as_member: TestClient) -> None:
    huge = 10**30
    assert as_member.put(f"/api/posts/{huge}/reactions/like").status_code == 422
    assert as_member.delete(f"/api/posts/{huge}/reactions/like").status_code == 422
    assert as_member.get("/api/reactions/mine", params={"post_ids": f"1,{huge}"}).status_code == 422
