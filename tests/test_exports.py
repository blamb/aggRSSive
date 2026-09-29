"""OPML for tags, headings and the whole collection; RSS for a single source (bookmark lists, watched pages)."""

import os
import tempfile

import pytest

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/exports.db"
os.environ["SECRET_KEY"] = "test-key"

from fastapi.testclient import TestClient  # noqa: E402

from aggrssive import classification, scheduler  # noqa: E402
from aggrssive.db import SessionLocal, init_db  # noqa: E402
from aggrssive.feeds.opml import parse_opml  # noqa: E402
from aggrssive.main import app  # noqa: E402
from aggrssive.models import Item, Source, Tag, User  # noqa: E402


@pytest.fixture(scope="module")
def client():
    init_db()
    scheduler.start = lambda: None
    scheduler.stop = lambda: None
    with SessionLocal() as db:
        classification.seed(db)
        u = User(email="ex@example.edu", display_name="Ex")
        db.add(u)
        db.flush()
        t = Tag(name="exports tag")
        feed = Source(feed_url="https://ex.test/feed", title="Ex Feed", site_url="https://ex.test", added_by_id=u.id)
        feed.tags.append(t)
        feed.categories.append(classification.get(db, "lcc:LB"))
        marks = Source(feed_url=f"bookmarks://{u.id}/readings", title="Readings", kind="bookmarks", added_by_id=u.id)
        marks.tags.append(t)
        db.add_all([feed, marks])
        db.flush()
        db.add(Item(source_id=marks.id, guid="https://ex.test/a", url="https://ex.test/a", title="A bookmarked page", text="notes", summary="<p>notes</p>"))
        db.commit()
    return TestClient(app)


def test_tag_and_heading_and_everything_opml(client):
    r = client.get("/tags/exports%20tag.opml")
    assert r.status_code == 200 and "opml" in r.headers["content-type"]
    entries = {e.title: e for e in parse_opml(r.content)}
    assert entries["Ex Feed"].feed_url == "https://ex.test/feed" and "exports tag" in entries["Ex Feed"].folders
    assert entries["Readings"].feed_url.endswith("/feed.rss")  # a bookmark list is exported by its aggRSSive feed
    r = client.get("/classification/lcc/L.opml")  # the parent heading includes LB
    assert "Ex Feed" in [e.title for e in parse_opml(r.content)]
    r = client.get("/sources.opml")
    assert r.status_code == 200 and len(parse_opml(r.content)) >= 2
    assert client.get("/tags/nope.opml").status_code == 404


def test_source_feed_serves_a_bookmark_list_as_rss(client):
    with SessionLocal() as db:
        sid = db.query(Source).filter_by(kind="bookmarks", title="Readings").one().id
    r = client.get(f"/sources/{sid}/feed.rss")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/rss+xml")
    assert "<title>Readings</title>" in r.text and "A bookmarked page" in r.text and 'rel="self"' in r.text


def test_pages_show_feed_links_with_copy_buttons(client):
    r = client.get("/tags/exports%20tag")
    assert "OPML of these sources" in r.text and 'class="copy" data-copy="' in r.text and ".opml" in r.text
    assert "OPML of every feed here" in client.get("/find").text


def test_feeds_and_pages_carry_enclosures(client):
    with SessionLocal() as db:
        lst = db.query(Source).filter_by(kind="bookmarks", title="Readings").one()
        db.add(Item(source_id=lst.id, guid="ep", url="https://ex.test/ep", title="An episode", text="", enclosure_url="https://cdn.ex.test/ep.mp3", enclosure_type="audio/mpeg", enclosure_length=100))
        db.commit()
        sid = lst.id
    r = client.get(f"/sources/{sid}/feed.rss")
    assert '<enclosure url="https://cdn.ex.test/ep.mp3" type="audio/mpeg" length="100"/>' in r.text
    r = client.get(f"/sources/{sid}")
    assert '<audio class="episode" controls preload="none" src="https://cdn.ex.test/ep.mp3"></audio>' in r.text
