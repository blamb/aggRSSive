"""Watched pages: links mode, changes mode, and the fetch flow through fetch_source."""

import os
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/watch.db"
os.environ["SECRET_KEY"] = "test-key"

from aggrssive.db import SessionLocal, init_db  # noqa: E402
from aggrssive.feeds import watch  # noqa: E402
from aggrssive.feeds.fetch import fetch_source  # noqa: E402
from aggrssive.models import Item, Source, User  # noqa: E402

PAGE = """<html><head><title>Dept News</title></head><body>
<nav><a href="/about">About the department</a><a href="/people">People and contacts</a></nav>
<main><ul>
<li><a href="/news/2026/new-lab">Department opens new teaching lab for first-years</a> — ribbon cut on Monday.</li>
<li><a href="/news/2026/grant">Faculty win national grant for open textbook project</a></li>
<li><a href="/tag/x">x</a></li>
<li><a href="https://elsewhere.example/story">Short ext</a></li>
</ul></main>
<footer><a href="/privacy">Privacy policy and terms of use</a></footer></body></html>"""

PAGE2 = PAGE.replace("<li><a href=\"/news/2026/grant\">", "<li><a href=\"/news/2026/talk\">Public talk on assessment next week</a></li>\n<li><a href=\"/news/2026/grant\">")

POLICY1 = "<html><body><main><h1>Policy</h1><p>Students may use AI tools with attribution. Late work loses ten percent.</p></main></body></html>"
POLICY2 = "<html><body><main><h1>Policy</h1><p>Students may use AI tools with attribution. Late work loses five percent. Extensions need a form.</p></main></body></html>"


def test_link_entries_skip_navigation_and_short_links():
    links = watch.link_entries(PAGE, "https://dept.example/news")
    assert [l["url"] for l in links] == ["https://dept.example/news/2026/new-lab", "https://dept.example/news/2026/grant"]
    assert links[0]["title"].startswith("Department opens") and "ribbon" in links[0]["excerpt"]


def test_change_summary_reports_added_and_removed():
    added, removed = watch.change_summary(watch.main_text(POLICY1), watch.main_text(POLICY2))
    assert any("five percent" in s for s in added) and any("Extensions" in s for s in added)
    assert any("ten percent" in s for s in removed)


def test_fetch_flow_for_both_kinds():
    init_db()
    with SessionLocal() as db:
        u = User(email="w@example.edu", display_name="W")
        db.add(u)
        db.flush()
        links = Source(feed_url="https://dept.example/news", kind="page", added_by_id=u.id)
        diff = Source(feed_url="https://dept.example/policy", kind="pagediff", added_by_id=u.id)
        db.add_all([links, diff])
        db.commit()
        pages = {"https://dept.example/news": PAGE, "https://dept.example/policy": POLICY1}
        fetch = lambda url: (pages[url], url)  # noqa: E731
        assert watch.fetch_page(db, links, fetch=fetch) == 2 and links.title == "Dept News"
        assert watch.fetch_page(db, links, fetch=fetch) == 0  # nothing new
        pages["https://dept.example/news"] = PAGE2
        assert watch.fetch_page(db, links, fetch=fetch) == 1
        assert db.query(Item).filter_by(source_id=links.id).count() == 3

        assert watch.fetch_page(db, diff, fetch=fetch) == 0 and diff.snapshot  # first look: snapshot only
        pages["https://dept.example/policy"] = POLICY2
        assert watch.fetch_page(db, diff, fetch=fetch) == 1
        item = db.query(Item).filter_by(source_id=diff.id).one()
        assert "changed" in item.title and "five percent" in item.summary and "Removed" in item.summary
        assert watch.fetch_page(db, diff, fetch=fetch) == 0

        # fetch_source routes page kinds here (network stubbed by failing fast on a bad host)
        bad = Source(feed_url="http://127.0.0.1:9/nothing", kind="page", added_by_id=u.id)
        db.add(bad)
        db.commit()
        assert fetch_source(db, bad) == 0 and bad.error_count == 1
