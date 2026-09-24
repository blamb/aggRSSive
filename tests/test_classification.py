"""Classification frameworks: data files, seeding, hierarchy, search, proposals."""

import os
import tempfile
from types import SimpleNamespace

import pytest

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/cls.db"
os.environ["SECRET_KEY"] = "test-key"

from aggrssive import classification as cl  # noqa: E402
from aggrssive.db import SessionLocal, init_db  # noqa: E402
from aggrssive.models import Category, Item, Source, User  # noqa: E402


@pytest.fixture(scope="module")
def db():
    init_db()
    with SessionLocal() as db:
        cl.seed(db)
        u = User(email="c@example.edu", display_name="C")
        db.add(u)
        db.flush()
        s = Source(feed_url="https://cls.test/feed", title="Open Ed Notes", description="teaching in higher education", added_by_id=u.id)
        db.add(s)
        db.flush()
        db.add(Item(source_id=s.id, guid="1", url="https://cls.test/1", title="Assessment redesign", text=""))
        db.commit()
        yield db


def src(db):
    return db.query(Source).filter_by(feed_url="https://cls.test/feed").one()


def test_data_files_load_with_sane_shapes():
    lcc, isced = cl.load("lcc"), cl.load("isced")
    assert 21 == sum(1 for n in lcc if n.depth == 0)
    assert 200 <= len(lcc) <= 260
    assert next(n for n in lcc if n.code == "LB").parent == "L"
    assert next(n for n in lcc if n.code == "DAW").parent == "D"
    assert next(n for n in lcc if n.code == "QA").hints.startswith("computer science")
    assert [n.code for n in isced if n.depth == 0][:3] == ["00", "01", "02"]
    assert next(n for n in isced if n.code == "0111").parent == "011" and next(n for n in isced if n.code == "0111").depth == 2
    assert len({n.code for n in isced}) == len(isced)  # no duplicate codes


def test_seed_is_idempotent(db):
    n = db.query(Category).count()
    assert n == len(cl.load("lcc")) + len(cl.load("isced"))
    assert cl.seed(db) == 0 and db.query(Category).count() == n


def test_lookup_ancestors_and_search(db):
    c = cl.get(db, "isced:0111")
    assert c and c.label == "Education science"
    assert [a.code for a in cl.ancestors(db, c)] == ["01", "011"]
    assert cl.get(db, "lcc:lb").code == "LB"  # case-insensitive
    assert cl.get(db, "nope:1") is None and cl.get(db, "garbage") is None
    labels = [x.label for x in cl.search(db, "educ")]
    assert "Theory and practice of education" in labels and "Education science" in labels


def test_decide_and_rollup_counts(db):
    s = src(db)
    s.suggested_categories = "lcc:LB\nisced:0111\nlcc:QA"
    db.commit()
    cl.decide(db, s, "lcc:LB", accept=True)
    cl.decide(db, s, "lcc:QA", accept=False)
    assert [c.code for c in s.categories] == ["LB"]
    assert s.suggested_categories == "isced:0111" and s.rejected_categories == "lcc:QA"
    counts = {n.code: c for n, c in cl.tree(db, "lcc")}
    assert counts["LB"] == 1 and counts["L"] == 1 and counts["Q"] == 0
    assert [x.feed_url for x in cl.sources_under(db, cl.get(db, "lcc:L"))] == ["https://cls.test/feed"]
    # refreshing without AI keeps the undecided proposal and never re-proposes rejected or accepted ones
    assert cl.refresh_suggestions(db, s, use_ai=False) == ["isced:0111"]


def test_ai_layer_validates_codes(db, monkeypatch):
    from aggrssive.config import get_settings

    monkeypatch.setattr(get_settings(), "anthropic_api_key", "sk-test")

    class FakeMessages:
        def create(self, **kw):
            assert "framework id: lcc" in kw["system"][0]["text"] and kw["system"][0]["cache_control"]["type"] == "ephemeral"
            return SimpleNamespace(content=[SimpleNamespace(type="text", text='{"lcc": ["lb", "ZZZ", "LC"], "isced": ["0111", "9999"]}')])

    import anthropic

    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: SimpleNamespace(messages=FakeMessages()))
    assert cl.ai_suggestions(db, src(db)) == ["lcc:LB", "lcc:LC", "isced:0111"]
