"""Roles: first account is full admin, site admins reach LTI settings, users don't; user management and sign-up toggle."""

import os
import tempfile

import pytest

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/roles.db"
os.environ["SECRET_KEY"] = "test-key"

from fastapi.testclient import TestClient  # noqa: E402

from aggrssive import scheduler  # noqa: E402
from aggrssive.auth import can_manage  # noqa: E402
from aggrssive.db import SessionLocal, init_db  # noqa: E402
from aggrssive.main import app  # noqa: E402
from aggrssive.models import User  # noqa: E402


@pytest.fixture(scope="module")
def clients():
    init_db()
    scheduler.start = lambda: None
    scheduler.stop = lambda: None
    with SessionLocal() as db:
        fresh = db.query(User).count() == 0
    with TestClient(app) as first, TestClient(app) as second:
        first.post("/signup", data={"email": "first-roles@example.edu", "display_name": "First", "password": "password123"})
        if not fresh:
            # Other test modules share this database; give "first" the role a first account would get.
            with SessionLocal() as db:
                u = db.query(User).filter_by(email="first-roles@example.edu").one()
                u.role, u.is_admin = "admin", True
                db.commit()
        second.post("/signup", data={"email": "second-roles@example.edu", "display_name": "Second", "password": "password123"})
        yield first, second


def role_of(email):
    with SessionLocal() as db:
        return db.query(User).filter_by(email=email).one()


def test_first_account_is_full_admin_second_is_user(clients):
    assert role_of("first-roles@example.edu").role == "admin"
    assert role_of("second-roles@example.edu").role == "user"


def test_permissions_by_role(clients):
    first, second = clients
    assert first.get("/admin").status_code == 200
    assert first.get("/admin/users").status_code == 200
    assert second.get("/admin", follow_redirects=False).status_code == 403
    assert second.get("/lti", follow_redirects=False).status_code == 403
    u = role_of("second-roles@example.edu")
    assert can_manage(u, u.id) and not can_manage(u, u.id + 1)
    a = role_of("first-roles@example.edu")
    assert can_manage(a, 999)


def test_full_admin_promotes_to_site_admin(clients):
    first, second = clients
    uid = role_of("second-roles@example.edu").id
    first.post(f"/admin/users/{uid}", data={"action": "role", "role": "site_admin"})
    assert role_of("second-roles@example.edu").role == "site_admin"
    assert second.get("/lti").status_code == 200  # site admin reaches LTI settings
    assert second.get("/admin/users", follow_redirects=False).status_code == 403  # but not user management


def test_cannot_demote_self_and_deactivation_blocks_login(clients):
    first, second = clients
    me = role_of("first-roles@example.edu").id
    first.post(f"/admin/users/{me}", data={"action": "role", "role": "user"})
    assert role_of("first-roles@example.edu").role == "admin"
    uid = role_of("second-roles@example.edu").id
    first.post(f"/admin/users/{uid}", data={"action": "deactivate"})
    assert second.get("/admin", follow_redirects=False).status_code in (303, 401)  # session no longer counts
    r = TestClient(app).post("/login", data={"email": "second-roles@example.edu", "password": "password123"})
    assert r.status_code == 400
    first.post(f"/admin/users/{uid}", data={"action": "activate"})


def test_signup_toggle_and_admin_created_accounts(clients):
    first, _ = clients
    first.post("/admin/settings", data={})  # unticked checkbox => closed
    assert TestClient(app).get("/signup").status_code == 403
    first.post("/admin/users", data={"display_name": "Invited", "email": "invited@example.edu", "role": "user", "password": "temporary1"})
    c = TestClient(app)
    assert c.post("/login", data={"email": "invited@example.edu", "password": "temporary1"}, follow_redirects=False).status_code == 303
    c.post("/account", data={"display_name": "Invited Person", "current_password": "temporary1", "new_password": "newpassword9"})
    assert role_of("invited@example.edu").display_name == "Invited Person"
    assert TestClient(app).post("/login", data={"email": "invited@example.edu", "password": "newpassword9"}, follow_redirects=False).status_code == 303
    first.post("/admin/settings", data={"allow_signup": "true"})
    assert TestClient(app).get("/signup").status_code == 200
