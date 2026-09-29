"""Email digests: rendering, due logic, sending only when there is something new, unsubscribe."""

import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/digest.db"
os.environ["SECRET_KEY"] = "test-key"

from fastapi.testclient import TestClient  # noqa: E402

from aggrssive import digest, scheduler  # noqa: E402
from aggrssive.config import get_settings  # noqa: E402
from aggrssive.db import SessionLocal, init_db  # noqa: E402
from aggrssive.main import app  # noqa: E402
from aggrssive.models import Bundle, Digest, Item, Source, User  # noqa: E402


@pytest.fixture(scope="module")
def client():
    init_db()
    scheduler.start = lambda: None
    scheduler.stop = lambda: None
    with SessionLocal() as db:
        u = User(email="reader@example.edu", display_name="Reader")
        db.add(u)
        db.flush()
        s = Source(feed_url="https://d.test/feed", title="D Feed", added_by_id=u.id)
        db.add(s)
        db.flush()
        db.add(Item(source_id=s.id, guid="1", url="https://d.test/1", title="Fresh post", text="Something new happened today.", published_at=datetime.now(timezone.utc) - timedelta(hours=2)))
        db.add(Item(source_id=s.id, guid="2", url="https://d.test/2", title="Old post", text="Ancient.", published_at=datetime.now(timezone.utc) - timedelta(days=30)))
        b = Bundle(owner_id=u.id, title="Digest Bundle", slug="digestb", is_public=True)
        b.sources.append(s)
        db.add(b)
        db.commit()
    c = TestClient(app)
    c.post("/login", data={"email": "reader@example.edu", "password": "x"})  # no password set; the subscribe test signs up its own user
    return c


def test_bundle_page_offers_digest_only_when_mail_configured(client, monkeypatch):
    c = TestClient(app)
    c.post("/signup", data={"email": "sub@example.edu", "display_name": "Sub", "password": "password123"})
    assert "<h3>By email</h3>" not in c.get("/bundles/digestb").text
    monkeypatch.setattr(get_settings(), "smtp_host", "smtp.test")
    monkeypatch.setattr(get_settings(), "smtp_from", "agg@test")
    assert "<h3>By email</h3>" in c.get("/bundles/digestb").text
    r = c.post("/bundles/digestb/digest", data={"frequency": "daily"}, follow_redirects=False)
    assert r.status_code == 303
    with SessionLocal() as db:
        d = db.query(Digest).join(User).filter(User.email == "sub@example.edu").one()
        assert d.frequency == "daily"
    assert "every day" in c.get("/bundles/digestb").text
    c.post("/bundles/digestb/digest", data={"frequency": "off"})
    with SessionLocal() as db:
        assert db.query(Digest).join(User).filter(User.email == "sub@example.edu").count() == 0


def test_run_sends_only_new_items_when_due(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "smtp_host", "smtp.test")
    monkeypatch.setattr(get_settings(), "smtp_from", "agg@test")
    sent = []
    with SessionLocal() as db:
        u = db.query(User).filter_by(email="reader@example.edu").one()
        b = db.query(Bundle).filter_by(slug="digestb").one()
        db.add(Digest(user_id=u.id, bundle_id=b.id, frequency="daily"))
        db.commit()
        hour = get_settings().digest_hour_utc
        wrong_hour = datetime(2026, 9, 29, (hour + 3) % 24, tzinfo=timezone.utc)
        assert digest.run(db, now=wrong_hour, sender=lambda *a: sent.append(a)) == 0
        due = datetime(2026, 9, 29, hour, 5, tzinfo=timezone.utc)
        monkeypatch.setattr(digest, "utcnow", lambda: datetime.now(timezone.utc))
        assert digest.run(db, now=due, sender=lambda *a: sent.append(a)) == 1
        to, subject, text, html = sent[0]
        assert to == "reader@example.edu" and subject == "Digest Bundle: 1 new item"
        assert "Fresh post" in text and "Old post" not in text and "Unsubscribe" in html and "/digests/unsubscribe/" in text
        # Same day again: not due. Next day, nothing new: nothing sent, but the check is recorded.
        assert digest.run(db, now=due + timedelta(hours=1), sender=lambda *a: sent.append(a)) == 0
        assert digest.run(db, now=due + timedelta(days=1), sender=lambda *a: sent.append(a)) == 0 and len(sent) == 1
        d = db.query(Digest).filter_by(user_id=u.id).one()
        assert d.last_sent_at is not None
        token = digest.unsubscribe_token(d)
    r = client.get(f"/digests/unsubscribe/{token}")
    assert r.status_code == 200 and "Digest Bundle" in r.text
    with SessionLocal() as db:
        assert db.query(Digest).count() == 0
    assert "Nothing changed" in client.get(f"/digests/unsubscribe/{token}").text
    assert "Nothing changed" in client.get("/digests/unsubscribe/garbage").text


def test_weekly_is_due_on_mondays_only():
    d = Digest(frequency="weekly", last_sent_at=None)
    hour = get_settings().digest_hour_utc
    assert digest.is_due(d, datetime(2026, 9, 28, hour, tzinfo=timezone.utc))  # a Monday
    assert not digest.is_due(d, datetime(2026, 9, 29, hour, tzinfo=timezone.utc))
