"""Anonymous accounts: created with an acknowledgement, entered by link, claimed with an email, removed by an admin."""

import os
import tempfile

import pytest

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/anon.db"
os.environ["SECRET_KEY"] = "test-key"

from fastapi.testclient import TestClient  # noqa: E402

from aggrssive import scheduler  # noqa: E402
from aggrssive.auth import set_setting  # noqa: E402
from aggrssive.db import SessionLocal, init_db  # noqa: E402
from aggrssive.main import app  # noqa: E402
from aggrssive.models import Bundle, User  # noqa: E402


@pytest.fixture(scope="module")
def admin():
    init_db()
    scheduler.start = lambda: None
    scheduler.stop = lambda: None
    with SessionLocal() as db:
        set_setting(db, "allow_signup", "true")
        set_setting(db, "allow_anonymous", "true")
        db.commit()
    c = TestClient(app)
    c.post("/signup", data={"email": "anon-admin@example.edu", "display_name": "Admin", "password": "password123"})
    with SessionLocal() as db:
        u = db.query(User).filter_by(email="anon-admin@example.edu").one()
        u.role, u.is_admin = "admin", True
        db.commit()
    return c


def test_create_needs_acknowledgement_then_shows_link(admin):
    c = TestClient(app)
    assert "try it without one" in c.get("/login").text
    r = c.post("/anonymous", data={}, follow_redirects=False)
    assert r.status_code == 400 and "Tick the box" in r.text
    r = c.post("/anonymous", data={"acknowledge": "true"}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/account?m=welcome"
    page = c.get("/account").text
    assert "Your way back in" in page and "/enter/" in page and "Change password" not in page
    with SessionLocal() as db:
        u = db.query(User).filter_by(is_anonymous=True).one()
        assert u.email.endswith("@anonymous.invalid") and u.login_token and u.display_name == "Anonymous"
        token = u.login_token
        db.add(Bundle(owner_id=u.id, title="Anon list", slug="anonlist1"))
        db.commit()
    # A fresh browser signs in through the link; a wrong link does not.
    c2 = TestClient(app)
    assert c2.get(f"/enter/{token}", follow_redirects=False).status_code == 303
    assert "Your way back in" in c2.get("/account").text
    assert c2.get("/enter/not-a-token").status_code == 404


def test_claim_turns_it_into_a_regular_account(admin):
    with SessionLocal() as db:
        token = db.query(User).filter_by(is_anonymous=True).one().login_token
    c = TestClient(app)
    c.get(f"/enter/{token}")
    r = c.post("/account/claim", data={"email": "claimed@example.edu", "password": "password123"}, follow_redirects=False)
    assert r.headers["location"] == "/account?m=claimed"
    with SessionLocal() as db:
        u = db.query(User).filter_by(email="claimed@example.edu").one()
        assert not u.is_anonymous and u.login_token is None and u.password_hash and db.query(Bundle).filter_by(owner_id=u.id).count() == 1
    assert TestClient(app).get(f"/enter/{token}").status_code == 404  # the link is dead
    c3 = TestClient(app)
    assert c3.post("/login", data={"email": "claimed@example.edu", "password": "password123"}, follow_redirects=False).status_code == 303


def test_admin_switch_and_removal(admin):
    c = TestClient(app)
    c.post("/anonymous", data={"acknowledge": "true"})
    with SessionLocal() as db:
        anon = db.query(User).filter_by(is_anonymous=True).one()
        db.add(Bundle(owner_id=anon.id, title="Spam", slug="spamlist1"))
        db.commit()
        aid = anon.id
    page = admin.get("/admin/users").text
    assert "anonymous" in page and 'value="delete"' in page
    r = admin.post(f"/admin/users/{aid}", data={"action": "delete"}, follow_redirects=False)
    assert r.status_code == 303
    with SessionLocal() as db:
        assert db.get(User, aid) is None and db.query(Bundle).filter_by(slug="spamlist1").count() == 0
    admin.post("/admin/settings", data={"allow_signup": "true"})  # anonymous box unticked -> off
    assert TestClient(app).get("/anonymous").status_code == 403
    assert "try it without one" not in TestClient(app).get("/login").text
    admin.post("/admin/settings", data={"allow_signup": "true", "allow_anonymous": "true"})
