"""Tag suggestions: heuristics, the Claude layer (with a fake client), and accept/edit/reject."""

import os
import tempfile
from types import SimpleNamespace

import pytest

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/tags.db"
os.environ["SECRET_KEY"] = "test-key"

from aggrssive import tagging  # noqa: E402
from aggrssive.db import SessionLocal, init_db  # noqa: E402
from aggrssive.models import Item, Source, Tag, User  # noqa: E402


@pytest.fixture(scope="module")
def db():
    init_db()
    with SessionLocal() as db:
        u = User(email="t@example.edu", display_name="T")
        db.add(u)
        db.flush()
        for name in ("open education", "edtech", "podcast", "assessment"):
            db.add(Tag(name=name))
        s = Source(feed_url="https://x.test/feed", title="Notes on Open Education", description="edtech musings", added_by_id=u.id)
        db.add(s)
        db.flush()
        for i in range(6):
            db.add(Item(source_id=s.id, guid=str(i), url=f"https://x.test/{i}", title=f"Post {i} about open education", categories="OER\nTeaching" if i % 2 else "OER\nUncategorized", text=""))
        db.commit()
        yield db


def source(db):
    return db.query(Source).filter(Source.feed_url == "https://x.test/feed").one()


def test_heuristics_find_vocabulary_and_feed_categories(db):
    got = tagging.heuristic_suggestions(db, source(db))
    assert got[0] == "open education"  # appears in title and every item
    assert "edtech" in got and "oer" in got and "teaching" in got
    assert "uncategorized" not in got and "podcast" not in got


def test_refresh_excludes_existing_and_rejected(db):
    s = source(db)
    tagging.decide(db, s, "teaching", accept=False)
    tagging.decide(db, s, "edtech", accept=True)
    pending = tagging.refresh_suggestions(db, s)
    assert "teaching" not in pending and "edtech" not in pending
    assert {t.name for t in s.tags} == {"edtech"}
    assert "open education" in pending


def test_accept_creates_tag_when_new(db):
    s = source(db)
    s.suggested_tags = "brand new tag\noer"
    db.commit()
    tagging.decide(db, s, "Brand New Tag", accept=True)
    assert "brand new tag" in {t.name for t in s.tags}
    assert s.suggested_tags == "oer"


def test_ai_layer_parses_and_normalizes(db, monkeypatch):
    from aggrssive.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-test")

    class FakeMessages:
        def create(self, **kw):
            assert "Existing vocabulary" in kw["messages"][0]["content"]
            return SimpleNamespace(content=[SimpleNamespace(type="text", text='Sure:\n["Open Education", "  higher-ed ", 42, ""]')])

    class FakeClient:
        def __init__(self, **kw):
            self.messages = FakeMessages()

    import anthropic

    monkeypatch.setattr(anthropic, "Anthropic", FakeClient)
    assert tagging.ai_suggestions(db, source(db)) == ["open education", "higher-ed"]


def test_ai_layer_off_without_key(db, monkeypatch):
    from aggrssive.config import get_settings

    monkeypatch.setattr(get_settings(), "anthropic_api_key", "")
    assert tagging.ai_suggestions(db, source(db)) == []
