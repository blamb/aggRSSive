"""OPML category attribute -> classification, and the starter collections page/import."""

import os
import tempfile

import pytest

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/col.db"
os.environ["SECRET_KEY"] = "test-key"

from fastapi.testclient import TestClient  # noqa: E402

from aggrssive import classification, scheduler  # noqa: E402
from aggrssive.db import SessionLocal, init_db  # noqa: E402
from aggrssive.feeds.opml import parse_opml  # noqa: E402
from aggrssive.main import app  # noqa: E402
from aggrssive.models import Source, User  # noqa: E402
from aggrssive.routes import admin as admin_routes  # noqa: E402

OPML = b"""<opml version="2.0"><head><title>Test starter</title></head><body>
<outline text="open education"><outline type="rss" text="A" xmlUrl="https://col-a.test/feed" htmlUrl="https://col-a.test" category="/lcc/LC,/isced/0111"/></outline>
<outline text="libraries"><outline type="rss" text="B" xmlUrl="https://col-b.test/feed" category="/lcc/Z"/>
<outline type="rss" text="A" xmlUrl="https://col-a.test/feed" category="/lcc/LB"/></outline>
</body></opml>"""


def test_category_attribute_parses_and_merges():
    entries = {e.feed_url: e for e in parse_opml(OPML)}
    assert entries["https://col-a.test/feed"].categories == ["lcc:LC", "isced:0111", "lcc:LB"]
    assert entries["https://col-a.test/feed"].folders == ["open education", "libraries"]
    assert entries["https://col-b.test/feed"].categories == ["lcc:Z"]


@pytest.fixture(scope="module")
def admin_client(tmp_path_factory):
    init_db()
    scheduler.start = lambda: None
    scheduler.stop = lambda: None
    scheduler.fetch_soon = lambda sid: None
    d = tmp_path_factory.mktemp("collections")
    (d / "test-starter.opml").write_bytes(OPML)
    admin_routes.COLLECTIONS = d
    with SessionLocal() as db:
        classification.seed(db)
    c = TestClient(app)
    c.post("/signup", data={"email": "col-admin@example.edu", "display_name": "Col", "password": "password123"})
    with SessionLocal() as db:
        u = db.query(User).filter_by(email="col-admin@example.edu").one()
        u.role, u.is_admin = "site_admin", False
        db.commit()
    return c


def test_collections_page_and_import_apply_tags_and_classification(admin_client):
    r = admin_client.get("/admin/collections")
    assert r.status_code == 200 and "Test starter" in r.text and "Import 2 new feeds" in r.text
    r = admin_client.post("/admin/collections/test-starter/import", follow_redirects=False)
    assert r.status_code == 303 and "2+new+feeds" in r.headers["location"]
    with SessionLocal() as db:
        a = db.query(Source).filter_by(feed_url="https://col-a.test/feed").one()
        assert {t.name for t in a.tags} == {"open education", "libraries"}
        assert {f"{c.framework}:{c.code}" for c in a.categories} == {"lcc:LC", "isced:0111", "lcc:LB"}
    # second import is a no-op
    r = admin_client.post("/admin/collections/test-starter/import", follow_redirects=False)
    assert "0+new+feeds" in r.headers["location"]
    assert "Import 0 new feeds" in admin_client.get("/admin/collections").text
