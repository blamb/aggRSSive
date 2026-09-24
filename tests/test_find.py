"""Find feeds: search across tags, headings and sources; one-click bundles from a tag or heading."""

import os
import tempfile

import pytest

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/find.db"
os.environ["SECRET_KEY"] = "test-key"

from fastapi.testclient import TestClient  # noqa: E402

from aggrssive import classification, scheduler  # noqa: E402
from aggrssive.db import SessionLocal, init_db  # noqa: E402
from aggrssive.main import app  # noqa: E402
from aggrssive.models import Bundle, Source, Tag, User  # noqa: E402


@pytest.fixture(scope="module")
def client():
    init_db()
    scheduler.start = lambda: None
    scheduler.stop = lambda: None
    scheduler.fetch_soon = lambda sid: None
    with SessionLocal() as db:
        classification.seed(db)
        u = User(email="find@example.edu", display_name="Finder", password_hash=None)
        db.add(u)
        db.flush()
        t = Tag(name="critical pedagogy")
        s1 = Source(feed_url="https://find1.test/feed", title="Hybrid Teaching Notes", description="critical digital pedagogy", added_by_id=u.id)
        s2 = Source(feed_url="https://find2.test/feed", title="Library Signals", added_by_id=u.id)
        s1.tags.append(t)
        s1.categories.append(classification.get(db, "lcc:LB"))
        s2.categories.append(classification.get(db, "lcc:ZA"))
        db.add_all([s1, s2])
        db.commit()
    c = TestClient(app)
    c.post("/signup", data={"email": "finder2@example.edu", "display_name": "F2", "password": "password123"})
    return c


def test_find_page_lists_tags_and_both_frameworks(client):
    r = client.get("/find")
    assert r.status_code == 200
    assert "critical pedagogy" in r.text and "Library of Congress Classification" in r.text and "ISCED-F 2013" in r.text


def test_search_hits_tags_headings_and_sources(client):
    r = client.get("/find", params={"q": "pedagog"})
    assert "critical pedagogy" in r.text and "Hybrid Teaching Notes" in r.text
    r = client.get("/find", params={"q": "libr"})
    assert "Library Signals" in r.text and "Information resources" in r.text  # ZA heading matches


def test_quick_bundle_from_heading_includes_descendants(client):
    r = client.post("/bundles/from", data={"cat": "lcc:L"}, follow_redirects=False)
    assert r.status_code == 303
    slug = r.headers["location"].split("/")[2]
    with SessionLocal() as db:
        b = db.query(Bundle).filter_by(slug=slug).one()
        urls = {s.feed_url for s in b.sources}  # other test modules may have filed sources under L too
        assert b.title == "L Education" and "https://find1.test/feed" in urls and "https://find2.test/feed" not in urls


def test_quick_bundle_from_tag(client):
    r = client.post("/bundles/from", data={"tag": "critical pedagogy"}, follow_redirects=False)
    assert r.status_code == 303
    assert client.post("/bundles/from", data={"tag": "no-such-tag"}).status_code == 404


def test_fork_copies_sources_and_rules_privately(client):
    r = client.post("/bundles/from", data={"tag": "critical pedagogy"}, follow_redirects=False)
    slug = r.headers["location"].split("/")[2]
    client.post(f"/bundles/{slug}/rules", data={"kind": "exclude", "field": "any", "pattern": "webinar"})
    r = client.post(f"/bundles/{slug}/fork", follow_redirects=False)
    assert r.status_code == 303
    copy_slug = r.headers["location"].split("/")[2]
    with SessionLocal() as db:
        from aggrssive.models import Rule

        orig = db.query(Bundle).filter_by(slug=slug).one()
        copy = db.query(Bundle).filter_by(slug=copy_slug).one()
        assert copy.title == "critical pedagogy (copy)" and copy.is_public is False
        assert [s.id for s in copy.sources] == [s.id for s in orig.sources]
        assert [r.pattern for r in db.query(Rule).filter_by(owner_type="bundle", owner_id=copy.id)] == ["webinar"]


def test_search_page_shows_feeds_writing_about_this(client, monkeypatch):
    from aggrssive import semantic
    from aggrssive.models import Item

    with SessionLocal() as db:
        s = db.query(Source).filter_by(title="Library Signals").one()
        db.add(Item(source_id=s.id, guid="m1", url="https://find2.test/m1", title="Weeding the reference collection", text=""))
        db.commit()
        sid = s.id
    monkeypatch.setattr(semantic, "search", lambda db, q, **kw: {"posts": [(db.query(Item).filter_by(guid="m1").one(), 0.7)], "sources": [(sid, 0.7, 1)], "analysed": 1, "pending": 0})
    r = client.get("/find", params={"q": "library collections"})
    assert "Feeds writing about this" in r.text and "1 post about this" in r.text and "Weeding the reference collection" in r.text
