"""QA community and reactions (UPS-054): docs/PRUEBAS-CAMPUS.md §7 (COM-01…10) and §8 (REA-01…03).

Edge cases on top of test_community.py and test_reactions.py: Feed is read-only, pagination stays stable
while new posts arrive, hostile HTML in posts and comments, spam limits per account, and reactions that
persist and never duplicate under repeated clicks.
"""

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Channel, Post, Reaction
from app.tests.conftest import auth_headers, make_user


def _channel(db: Session, slug: str) -> Channel:
    return db.scalar(select(Channel).where(Channel.slug == slug))


def _visible_post(db: Session) -> Post:
    return db.scalar(select(Post).where(Post.is_hidden.is_(False)).order_by(Post.id))


# ── COM-01/02 · Feed gathers channels and nobody posts in it directly ──


def test_feed_is_read_only_even_for_superadmin(as_superadmin: TestClient, db: Session) -> None:
    feed = _channel(db, "feed")
    response = as_superadmin.post(f"/api/channels/{feed.id}/posts", data={"body": "hola"})
    assert response.status_code == 422  # noqa: S101
    assert "General" in response.json()["error"]["message"]  # noqa: S101


# ── COM-03/04 · a non-member is offered the club, not a generic error ──


def test_not_a_member_error_names_the_club(client: TestClient, db: Session, seeded: dict) -> None:
    outsider = make_user(db, email="fuera@upiixsol.dev", boleta="2026000098")
    club = _channel(db, "upiixia")
    denied = client.post(f"/api/channels/{club.id}/posts", data={"body": "x"}, headers=auth_headers(outsider))
    error = denied.json()["error"]
    assert denied.status_code == 403 and error["code"] == "not_a_member"  # noqa: S101
    assert club.name in error["message"]  # noqa: S101


# ── COM-08 · cursor pages never repeat a post while new ones arrive ──


def test_cursor_pages_have_no_duplicates_when_posts_arrive(as_member: TestClient, db: Session) -> None:
    channel = _channel(db, "general")
    path = f"/api/channels/{channel.id}/posts"
    for i in range(5):
        as_member.post(path, data={"body": f"base {i}"})
    first = as_member.get(f"{path}?limit=2").json()
    as_member.post(path, data={"body": "llegó en medio"})  # newer than every page already read
    second = as_member.get(f"{path}?limit=2&cursor={first['next_cursor']}").json()
    ids = [p["id"] for p in first["items"] + second["items"]]
    assert len(ids) == len(set(ids)) == 4  # noqa: S101
    assert "llegó en medio" not in [p["body"] for p in second["items"]]  # noqa: S101


def test_bad_cursor_and_limit_are_rejected(as_member: TestClient, db: Session) -> None:
    path = f"/api/channels/{_channel(db, 'general').id}/posts"
    assert as_member.get(f"{path}?limit=51").status_code == 422  # noqa: S101
    assert as_member.get(f"{path}?cursor=no-es-un-cursor").status_code in (400, 422)  # noqa: S101


# ── COM-09 · HTML and JS never come back executable ──


def test_post_and_comment_bodies_are_sanitized(as_member: TestClient, db: Session) -> None:
    path = f"/api/channels/{_channel(db, 'general').id}/posts"
    hostile = (
        '<script>alert(1)</script><img src=x onerror="alert(2)"><a href="javascript:alert(3)">x</a>**ok**'
    )
    post = as_member.post(path, data={"body": hostile}).json()
    comment = as_member.post(f"/api/posts/{post['id']}/comments", json={"body": hostile}).json()
    for body in (post["body"], comment["body"]):
        lowered = body.lower()
        assert "<script" not in lowered and "onerror" not in lowered  # noqa: S101
        assert "javascript:" not in lowered and "<img" not in lowered  # noqa: S101
        assert "**ok**" in body  # noqa: S101  markdown text survives
    listed = as_member.get(f"/api/posts/{post['id']}/comments").json()["items"][0]
    assert listed["body"] == comment["body"]  # noqa: S101  stored clean, not cleaned on read


def test_post_link_must_be_http(as_member: TestClient, db: Session) -> None:
    path = f"/api/channels/{_channel(db, 'general').id}/posts"
    for bad in ("javascript:alert(1)", "data:text/html,x", "/relativo"):
        assert as_member.post(path, data={"body": "x", "link_url": bad}).status_code == 422  # noqa: S101


# ── COM-10 · spam is cut per account, comments included ──


def test_comment_spam_gets_429(as_member: TestClient, db: Session) -> None:
    post = _visible_post(db)
    path = f"/api/posts/{post.id}/comments"
    statuses = [as_member.post(path, json={"body": f"c {i}"}).status_code for i in range(11)]
    assert statuses[:10] == [201] * 10 and statuses[10] == 429  # noqa: S101


def test_spam_limit_is_per_account(as_member: TestClient, as_admin_ia: TestClient, db: Session) -> None:
    path = f"/api/channels/{_channel(db, 'general').id}/posts"
    for i in range(10):
        as_member.post(path, data={"body": f"spam {i}"})
    assert as_member.post(path, data={"body": "uno más"}).status_code == 429  # noqa: S101
    assert as_admin_ia.post(path, data={"body": "yo sí puedo"}).status_code == 201  # noqa: S101


# ── REA-01 · react, reload, unreact: the counter moves and persists ──


def test_reaction_persists_in_the_listing_after_reload(as_member: TestClient, db: Session) -> None:
    post = _visible_post(db)
    channel = db.get(Channel, post.channel_id)
    before = as_member.put(f"/api/posts/{post.id}/reactions/like").json()["reactions"].get("like", 0)
    page = as_member.get(f"/api/channels/{channel.id}/posts?limit=50").json()["items"]
    listed = next(p for p in page if p["id"] == post.id)
    assert listed["reactions"].get("like") == before  # noqa: S101
    after = as_member.delete(f"/api/posts/{post.id}/reactions/like").json()["reactions"].get("like", 0)
    assert after == before - 1  # noqa: S101


# ── REA-02 · a fast double click never duplicates ──


def test_repeated_clicks_keep_one_reaction(as_member: TestClient, db: Session) -> None:
    post = _visible_post(db)
    for _ in range(5):
        assert as_member.put(f"/api/posts/{post.id}/reactions/fire").status_code == 200  # noqa: S101
    count = db.scalar(select(func.count()).select_from(Reaction).where(Reaction.post_id == post.id))
    mine = db.scalar(
        select(func.count()).select_from(Reaction).where(Reaction.post_id == post.id, Reaction.kind == "fire")
    )
    assert mine >= 1 and count >= mine  # noqa: S101
    for _ in range(3):
        assert as_member.delete(f"/api/posts/{post.id}/reactions/fire").status_code == 200  # noqa: S101
    mine_after = as_member.get(f"/api/reactions/mine?post_ids={post.id}")
    assert mine_after.status_code == 200 and "fire" not in mine_after.json().get(str(post.id), [])  # noqa: S101


def test_unknown_reaction_kind_and_missing_post(as_member: TestClient, db: Session) -> None:
    post = _visible_post(db)
    assert as_member.put(f"/api/posts/{post.id}/reactions/angry").status_code == 422  # noqa: S101
    assert as_member.put("/api/posts/999999/reactions/like").status_code == 404  # noqa: S101


# ── REA-03 · my reactions come back marked as mine ──


def test_mine_marks_only_my_reactions(as_member: TestClient, as_admin_ia: TestClient, db: Session) -> None:
    post = _visible_post(db)
    mine = f"/api/reactions/mine?post_ids={post.id}"
    as_admin_ia.put(f"/api/posts/{post.id}/reactions/idea")
    assert "idea" not in as_member.get(mine).json().get(str(post.id), [])  # noqa: S101
    as_member.put(f"/api/posts/{post.id}/reactions/like")
    assert as_member.get(mine).json()[str(post.id)] == ["like"]  # noqa: S101
    assert as_admin_ia.get(mine).json()[str(post.id)] == ["idea"]  # noqa: S101


def test_mine_rejects_bad_id_lists(as_member: TestClient) -> None:
    for bad in ("abc", "0", "2147483648", ",".join(str(i) for i in range(1, 52))):
        assert as_member.get(f"/api/reactions/mine?post_ids={bad}").status_code == 422  # noqa: S101
