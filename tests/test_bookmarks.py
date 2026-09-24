"""Bookmark lists: metadata extraction from a page, saving, bundling, and the scheduler leaving them alone."""

import os
import tempfile

import pytest

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/bm.db"
os.environ["SECRET_KEY"] = "test-key"

from fastapi.testclient import TestClient  # noqa: E402

from aggrssive import scheduler  # noqa: E402
from aggrssive.db import SessionLocal, init_db  # noqa: E402
from aggrssive.feeds import bookmarks as bm  # noqa: E402
from aggrssive.main import app  # noqa: E402
from aggrssive.models import Bundle, Item, Source, User  # noqa: E402
from aggrssive.routes import bookmarks as bmroutes  # noqa: E402
from aggrssive.rules import bundle_items  # noqa: E402

PAGE = """<html><head><title>Why Open Pedagogy Matters | Hybrid Notes</title>
<meta property="og:title" content="Why Open Pedagogy Matters"><meta property="og:site_name" content="Hybrid Notes">
<meta property="og:description" content="A short case for letting students make the syllabus.">
<meta property="og:image" content="/img/cover.jpg"><meta property="article:published_time" content="2026-09-01T10:00:00+00:00">
<meta name="author" content="R. Example"><link rel="canonical" href="https://hybrid.example/open-pedagogy">
</head><body><p>First paragraph.</p></body></html>"""

LD_PAGE = """<html><head><title>Plain title</title>
<script type="application/ld+json">{"@context":"https://schema.org","@graph":[{"@type":"WebSite"},{"@type":"BlogPosting","headline":"Structured headline","description":"From JSON-LD","author":{"@type":"Person","name":"L. D. Author"},"datePublished":"2026-08-15","image":{"@type":"ImageObject","url":"https://x.example/i.png"}}]}</script>
</head><body></body></html>"""


def test_parse_page_prefers_open_graph_and_canonical():
    e = bm.parse_page(PAGE, "https://hybrid.example/open-pedagogy?utm=1")
    assert e.title == "Why Open Pedagogy Matters" and e.site_name == "Hybrid Notes"
    assert e.description.startswith("A short case") and e.author == "R. Example"
    assert e.image_url == "https://hybrid.example/img/cover.jpg" and e.url == "https://hybrid.example/open-pedagogy"
    assert e.published_at.year == 2026 and e.published_at.month == 9


def test_parse_page_falls_back_to_json_ld():
    e = bm.parse_page(LD_PAGE, "https://x.example/p")
    assert e.title == "Structured headline" and e.description == "From JSON-LD" and e.author == "L. D. Author"
    assert e.image_url == "https://x.example/i.png" and e.published_at.day == 15


def test_extract_never_raises():
    import httpx

    def boom(url):
        raise httpx.ConnectError("nope")

    e = bm.extract("https://down.example/x", fetch=boom)
    assert e.url == "https://down.example/x" and e.error and "Could not read" in e.error


@pytest.fixture(scope="module")
def client():
    init_db()
    scheduler.start = lambda: None
    scheduler.stop = lambda: None
    bmroutes.extract = lambda url: bm.parse_page(PAGE, url)
    c = TestClient(app)
    c.post("/signup", data={"email": "bm@example.edu", "display_name": "Marker", "password": "password123"})
    return c


def test_list_bookmark_bundle_flow(client):
    r = client.post("/bookmarks/lists", data={"title": "Week 3 readings", "description": "for the seminar"}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("/bookmarks/add?list=")
    list_id = int(r.headers["location"].rsplit("=", 1)[1])

    r = client.get("/bookmarks/add", params={"url": "hybrid.example/open-pedagogy", "list": list_id})
    assert r.status_code == 200 and 'value="Why Open Pedagogy Matters"' in r.text and "R. Example" in r.text

    r = client.post("/bookmarks/items", data={"list_id": list_id, "url": "https://hybrid.example/open-pedagogy", "title": "Why Open Pedagogy Matters", "description": "A short case.", "note": "Read before Tuesday", "author": "R. Example", "published": "2026-09-01", "tags": "open pedagogy, week 3"}, follow_redirects=False)
    assert r.status_code == 303
    r = client.get(f"/sources/{list_id}")
    assert "Why Open Pedagogy Matters" in r.text and "Read before Tuesday" in r.text and "Fetch now" not in r.text and "bookmarks" in r.text

    # Saving the same page twice does not duplicate it.
    client.post("/bookmarks/items", data={"list_id": list_id, "url": "https://hybrid.example/open-pedagogy", "title": "dup"})
    with SessionLocal() as db:
        assert db.query(Item).filter_by(source_id=list_id).count() == 1
        item = db.query(Item).filter_by(source_id=list_id).one()
        assert item.categories == "open pedagogy\nweek 3" and item.published_at.month == 9 and item.author == "R. Example"
        u = db.query(User).filter_by(email="bm@example.edu").one()
        b = Bundle(owner_id=u.id, title="Seminar", slug="seminarbm", is_public=True)
        b.sources.append(db.get(Source, list_id))
        db.add(b)
        db.commit()
        assert [bi.item.title for bi in bundle_items(db, b)] == ["Why Open Pedagogy Matters"]
        item_id = item.id

    r = client.post(f"/bookmarks/items/{item_id}/delete", follow_redirects=False)
    assert r.status_code == 303
    with SessionLocal() as db:
        assert db.query(Item).filter_by(source_id=list_id).count() == 0


def test_scheduler_and_refresh_skip_bookmark_lists(client, monkeypatch):
    called = []
    monkeypatch.setattr(scheduler, "fetch_source", lambda db, s: called.append(s.feed_url))
    with SessionLocal() as db:
        lst = db.query(Source).filter_by(kind="bookmarks").first()
        lid = lst.id
    scheduler.fetch_one(lid)
    scheduler.poll_all()
    assert not [u for u in called if u.startswith("bookmarks://")]
    r = client.post(f"/sources/{lid}/refresh", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == f"/bookmarks/add?list={lid}"


def test_other_users_cannot_add_to_my_list(client):
    c2 = TestClient(app)
    c2.post("/signup", data={"email": "bm2@example.edu", "display_name": "Other", "password": "password123"})
    with SessionLocal() as db:
        lid = db.query(Source).filter_by(kind="bookmarks").first().id
    r = c2.post("/bookmarks/items", data={"list_id": lid, "url": "https://x.example/y", "title": "sneak"}, follow_redirects=False)
    assert r.status_code == 403


def test_author_from_json_ld_reference_and_rel_author():
    page = """<html><head><script type="application/ld+json">{"@graph":[{"@type":"Person","@id":"https://x.example/#me","name":"Ref Person"},{"@type":"Article","headline":"H","author":{"@id":"https://x.example/#me"}}]}</script></head></html>"""
    assert bm.parse_page(page, "https://x.example/a").author == "Ref Person"
    page = '<html><head><title>T</title></head><body><a rel="author" href="/about">Alan Levine</a></body></html>'
    assert bm.parse_page(page, "https://x.example/b").author == "Alan Levine"
