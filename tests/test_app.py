"""End-to-end through the HTTP layer, against a temporary database and stubbed fetching."""

import os
import tempfile

import pytest

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"
os.environ["SECRET_KEY"] = "test-key"

from fastapi.testclient import TestClient  # noqa: E402

from aggrssive import scheduler  # noqa: E402
from aggrssive.db import SessionLocal, init_db  # noqa: E402
from aggrssive.feeds import fetch as fetchmod  # noqa: E402
from aggrssive.main import app  # noqa: E402
from aggrssive.models import Item, Source  # noqa: E402

RSS = b"""<rss version="2.0"><channel><title>Stub</title><link>https://s.example</link>
<item><title>Open pedagogy roundup</title><link>https://s.example/1</link><guid>1</guid><description>notes</description></item>
<item><title>Vendor webinar</title><link>https://s.example/2</link><guid>2</guid><description>buy now</description></item>
<item><title>Open pedagogy roundup</title><link>https://s.example/1?utm=x</link><guid>3</guid><description>dupe</description></item>
</channel></rss>"""


class FakeResp:
    status_code = 200
    headers = {"content-type": "application/rss+xml"}
    content = RSS

    def raise_for_status(self):
        pass


class FakeClient:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass

    def get(self, url, headers=None):
        return FakeResp()


@pytest.fixture(scope="module")
def client(module_mocker=None):
    init_db()
    scheduler.start = lambda: None
    scheduler.stop = lambda: None
    scheduler.fetch_soon = lambda sid: None
    fetchmod.client = lambda: FakeClient()
    with TestClient(app) as c:
        yield c


def test_signup_add_source_bundle_and_outputs(client):
    r = client.post("/signup", data={"email": "b@example.edu", "display_name": "Brian", "password": "password123"}, follow_redirects=False)
    assert r.status_code == 303

    r = client.post("/sources", data={"feed_url": "https://s.example/feed", "title": "Stub", "tags": "OER, Teaching"}, follow_redirects=False)
    assert r.status_code == 303
    with SessionLocal() as db:
        s = db.query(Source).one()
        fetchmod.fetch_source(db, s)
        sid = s.id
        assert {t.name for t in s.tags} == {"oer", "teaching"}

    r = client.get(f"/sources/{sid}")
    assert "Open pedagogy roundup" in r.text

    r = client.post("/bundles", data={"title": "My aggRSSive", "source_ids": [str(sid)]}, follow_redirects=False)
    slug = r.headers["location"].split("/")[2]

    # dedupe on: the near-duplicate is collapsed
    data = client.get(f"/b/{slug}.json").json()
    assert [i["title"] for i in data["items"]] == ["Open pedagogy roundup", "Vendor webinar"]

    client.post(f"/bundles/{slug}/rules", data={"kind": "exclude", "field": "any", "pattern": "webinar"})
    data = client.get(f"/b/{slug}.json").json()
    assert [i["title"] for i in data["items"]] == ["Open pedagogy roundup"]

    # pin forces an excluded item back in, at the top
    with SessionLocal() as db:
        webinar_id = db.query(Item).filter(Item.title == "Vendor webinar").one().id
    client.post(f"/bundles/{slug}/items/{webinar_id}", data={"action": "pin"})
    data = client.get(f"/b/{slug}.json").json()
    assert data["items"][0]["title"] == "Vendor webinar" and data["items"][0]["pinned"] is True

    assert client.get(f"/b/{slug}/feed.rss").status_code == 200
    assert "<feed" in client.get(f"/b/{slug}/feed.atom").text
    assert client.get(f"/b/{slug}/feed.json").json()["version"].startswith("https://jsonfeed.org")
    assert "xmlUrl" in client.get(f"/b/{slug}/sources.opml").text
    js = client.get(f"/embed/{slug}.js").text
    assert slug in js and "__SLUG__" not in js
    assert "Open pedagogy" in client.get(f"/embed/{slug}/frame").text


def test_private_bundle_is_hidden_from_strangers(client):
    with SessionLocal() as db:
        sid = db.query(Source).one().id
    r = client.post("/bundles", data={"title": "Secret", "source_ids": [str(sid)]}, follow_redirects=False)
    slug = r.headers["location"].split("/")[2]
    client.post(f"/bundles/{slug}/edit", data={"title": "Secret", "is_public": "", "match_mode": "any", "max_items": "50"})
    anon = TestClient(app)
    assert anon.get(f"/b/{slug}.json").status_code == 404
    assert client.get(f"/b/{slug}.json").status_code == 200
