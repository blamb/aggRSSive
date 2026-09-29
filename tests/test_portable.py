"""Portable aggRSSives: export, parse, import into another account, curation applied as items exist."""

import io
import json
import os
import tempfile

import pytest

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/portable.db"
os.environ["SECRET_KEY"] = "test-key"

from fastapi.testclient import TestClient  # noqa: E402

from aggrssive import classification, portable, scheduler  # noqa: E402
from aggrssive.db import SessionLocal, init_db  # noqa: E402
from aggrssive.main import app  # noqa: E402
from aggrssive.models import Bundle, Item, ItemOverride, Rule, Source, Tag, User  # noqa: E402


@pytest.fixture(scope="module")
def setup():
    init_db()
    scheduler.start = lambda: None
    scheduler.stop = lambda: None
    scheduler.fetch_soon = lambda sid: None
    with SessionLocal() as db:
        classification.seed(db)
        owner = User(email="port-owner@example.edu", display_name="Owner")
        db.add(owner)
        db.flush()
        feed = Source(feed_url="https://port.test/feed", title="Port Feed", site_url="https://port.test", added_by_id=owner.id)
        feed.tags.append(Tag(name="portable tag"))
        feed.categories.append(classification.get(db, "lcc:LB"))
        marks = Source(feed_url=f"bookmarks://{owner.id}/readings", title="Readings", kind="bookmarks", added_by_id=owner.id)
        db.add_all([feed, marks])
        db.flush()
        i1 = Item(source_id=feed.id, guid="1", url="https://port.test/1", title="Pinned post", text="assessment rubrics")
        i2 = Item(source_id=marks.id, guid="https://elsewhere.test/a", url="https://elsewhere.test/a", title="A bookmark", summary="<p>why</p>", text="why")
        db.add_all([i1, i2])
        db.flush()
        b = Bundle(owner_id=owner.id, title="Portable Bundle", slug="portable1", is_public=True, match_mode="all", max_items=20)
        b.sources += [feed, marks]
        db.add(b)
        db.flush()
        db.add(Rule(owner_type="bundle", owner_id=b.id, kind="include", field="text", pattern="assessment"))
        db.add(ItemOverride(bundle_id=b.id, item_id=i1.id, pinned=True, note="read first"))
        db.commit()
        return {"slug": b.slug}


def test_export_carries_everything(setup):
    c = TestClient(app)
    r = c.get(f"/bundles/{setup['slug']}/export.json")
    assert r.status_code == 200 and r.headers["content-disposition"].endswith('.json"')
    doc = r.json()
    assert doc["format"] == portable.FORMAT_ONE and doc["bundle"]["match_mode"] == "all" and doc["bundle"]["max_items"] == 20
    srcs = {s["title"]: s for s in doc["sources"]}
    assert srcs["Port Feed"]["tags"] == ["portable tag"] and srcs["Port Feed"]["categories"] == ["lcc:LB"]
    assert srcs["Readings"]["kind"] == "bookmarks" and srcs["Readings"]["items"][0]["url"] == "https://elsewhere.test/a"
    assert doc["rules"] == [{"kind": "include", "field": "text", "pattern": "assessment", "is_regex": False, "threshold": 0.58}]
    assert doc["curation"] == [{"url": "https://port.test/1", "title": "Pinned post", "pinned": True, "hidden": False, "note": "read first"}]


def test_import_recreates_privately_for_another_person(setup):
    c = TestClient(app)
    doc = c.get(f"/bundles/{setup['slug']}/export.json").json()
    c2 = TestClient(app)
    c2.post("/signup", data={"email": "port-importer@example.edu", "display_name": "Importer", "password": "password123"})
    r = c2.post("/bundles/import", files={"file": ("x.json", io.BytesIO(json.dumps(doc).encode()), "application/json")}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].endswith("/edit")
    slug = r.headers["location"].split("/")[2]
    with SessionLocal() as db:
        b = db.query(Bundle).filter_by(slug=slug).one()
        assert b.owner.email == "port-importer@example.edu" and b.is_public is False and b.match_mode == "all"
        titles = sorted(s.title for s in b.sources)
        assert titles == ["Port Feed", "Readings"]
        feed = next(s for s in b.sources if s.title == "Port Feed")
        assert feed.feed_url == "https://port.test/feed" and db.query(Source).filter_by(feed_url="https://port.test/feed").count() == 1  # re-used, not duplicated
        marks = next(s for s in b.sources if s.title == "Readings")
        assert marks.kind == "bookmarks" and marks.added_by.email == "port-importer@example.edu" and db.query(Item).filter_by(source_id=marks.id).count() == 1
        assert db.query(Rule).filter_by(owner_type="bundle", owner_id=b.id).count() == 1
        o = db.query(ItemOverride).filter_by(bundle_id=b.id).one()  # the pinned item exists already, so curation applied at once
        assert o.pinned and o.note == "read first" and b.pending_curation is None
    r = c2.get("/account")
    assert "Export all 1 of mine" in r.text
    assert c2.get("/account/export.json").json()["format"] == portable.FORMAT_MANY


def test_pending_curation_waits_for_items(setup):
    with SessionLocal() as db:
        u = db.query(User).filter_by(email="port-owner@example.edu").one()
        doc = {"format": portable.FORMAT_ONE, "bundle": {"title": "Later"}, "sources": [{"feed_url": "https://later.test/feed", "title": "Later Feed"}], "rules": [], "curation": [{"url": "https://later.test/1", "pinned": True}]}
        b, new_ids = portable.import_bundle(db, doc, u)
        assert len(new_ids) == 1 and b.pending_curation and db.query(ItemOverride).filter_by(bundle_id=b.id).count() == 0
        db.add(Item(source_id=new_ids[0], guid="1", url="https://later.test/1", title="Arrived", text=""))
        db.commit()
        assert portable.apply_pending_curation(db, b) == 1 and b.pending_curation is None
        assert db.query(ItemOverride).filter_by(bundle_id=b.id).one().pinned


def test_bad_file_is_refused(setup):
    c = TestClient(app)
    c.post("/signup", data={"email": "port-x@example.edu", "display_name": "X", "password": "password123"})
    r = c.post("/bundles/import", files={"file": ("x.json", io.BytesIO(b"{\"nope\": 1}"), "application/json")})
    assert r.status_code == 400 and "isn't an aggRSSive export" in r.text
