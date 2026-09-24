"""Meaning rules (local embeddings, faked) and plain-language rules (GenAI, faked), with reasons."""

import os
import tempfile
from types import SimpleNamespace

import numpy as np
import pytest

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/sem.db"
os.environ["SECRET_KEY"] = "test-key"

from aggrssive import judge, rules, scheduler, semantic  # noqa: E402
from aggrssive.db import SessionLocal, init_db  # noqa: E402
from aggrssive.models import Bundle, Item, Judgement, Rule, Source, User  # noqa: E402

VOCAB = ["assessment", "grading", "rubric", "webinar", "vendor", "hockey", "annotation", "reading"]


def fake_embed(texts):
    """Deterministic bag-of-words vectors so similarity is predictable."""
    out = []
    for t in texts:
        v = np.array([float(w in t.lower()) for w in VOCAB], dtype=np.float32) + 1e-3
        out.append(v / np.linalg.norm(v))
    return out


@pytest.fixture(scope="module")
def data(monkeypatch_module=None):
    init_db()
    semantic.embed_texts = fake_embed
    semantic._rule_cache.clear()
    with SessionLocal() as db:
        u = User(email="sem@example.edu", display_name="Sem")
        db.add(u)
        db.flush()
        s = Source(feed_url="https://sem.test/feed", title="Sem", added_by_id=u.id)
        db.add(s)
        db.flush()
        titles = ["Assessment and grading with rubrics", "Vendor webinar next week", "Hockey season preview", "Students annotate reading assignments"]
        for n, t in enumerate(titles):
            db.add(Item(source_id=s.id, guid=str(n), url=f"https://sem.test/{n}", title=t, text=t))
        b = Bundle(owner_id=u.id, title="Sem bundle", slug="sembundle")
        b.sources.append(s)
        db.add(b)
        db.commit()
        assert semantic.embed_pending(db) >= 4  # other test modules share this database
        return {"bundle_id": b.id, "source_id": s.id}


def titles(items):
    return [bi.item.title for bi in items]


def test_meaning_rule_includes_similar_items_with_reasons(data):
    with SessionLocal() as db:
        db.add(Rule(owner_type="bundle", owner_id=data["bundle_id"], kind="include", field="semantic", pattern="assessment grading rubric", threshold=0.5))
        db.commit()
        b = db.get(Bundle, data["bundle_id"])
        included, excluded = rules.resolve(db, b, with_excluded=True)
        assert titles(included) == ["Assessment and grading with rubrics"]
        assert included[0].reason.startswith("included: meaning ≈")
        assert {bi.item.title: bi.reason for bi in excluded}["Hockey season preview"] == "no include rule matches"
        db.query(Rule).delete()
        db.commit()


def test_unanalysed_items_are_pending_not_dropped_by_exclude(data):
    with SessionLocal() as db:
        db.add(Rule(owner_type="bundle", owner_id=data["bundle_id"], kind="exclude", field="semantic", pattern="vendor webinar", threshold=0.5))
        db.commit()
        item = db.query(Item).filter_by(title="Vendor webinar next week").one()
        item.embedding = None  # not analysed yet
        db.commit()
        b = db.get(Bundle, data["bundle_id"])
        included, _ = rules.resolve(db, b, with_excluded=True)
        assert "Vendor webinar next week" in titles(included)  # exclude can't judge yet -> let through
        assert semantic.embed_pending(db) >= 1
        included, excluded = rules.resolve(db, b, with_excluded=True)
        assert "Vendor webinar next week" not in titles(included)
        assert any(bi.reason.startswith("excluded: meaning") for bi in excluded)
        db.query(Rule).delete()
        db.commit()


def test_plain_language_rule_judged_once_and_cached(data, monkeypatch):
    from aggrssive.config import get_settings

    monkeypatch.setattr(get_settings(), "anthropic_api_key", "sk-test")
    calls = []

    class FakeMessages:
        def create(self, **kw):
            calls.append(kw)
            ids = [line[1:].split("]")[0] for line in kw["messages"][0]["content"].splitlines() if line.startswith("[")]
            verdicts = {i: ("Hockey" not in kw["messages"][0]["content"].split(f"[{i}]")[1].split("\n")[0]) for i in ids}
            return SimpleNamespace(content=[SimpleNamespace(type="text", text=__import__("json").dumps(verdicts))])

    import anthropic

    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: SimpleNamespace(messages=FakeMessages()))
    with SessionLocal() as db:
        db.add(Rule(owner_type="bundle", owner_id=data["bundle_id"], kind="include", field="ai", pattern="anything except sports"))
        db.commit()
        b = db.get(Bundle, data["bundle_id"])
        included, excluded = rules.resolve(db, b, with_excluded=True)
        assert "Hockey season preview" not in titles(included) and len(included) == 3
        assert included[0].reason.startswith("included: GenAI")
        assert len(calls) == 1 and db.query(Judgement).count() == 4
        rules.resolve(db, b, with_excluded=True)
        assert len(calls) == 1  # verdicts cached; no second request
        assert judge.judge_pending(db) == 0  # nothing left to judge
        db.query(Rule).delete()
        db.commit()


def test_rule_form_validation_and_describe(data):
    from fastapi import HTTPException

    from aggrssive.routes.bundles import validate_rule

    assert validate_rule("include", "semantic", "x", "strict") == semantic.STRICTNESS["strict"]
    with pytest.raises(HTTPException):
        validate_rule("include", "nope", "x", "normal")
    r = Rule(owner_type="bundle", owner_id=1, kind="include", field="semantic", pattern="open pedagogy", threshold=0.75)
    assert rules.describe(r) == "meaning ≈ “open pedagogy” (strict)"
    assert scheduler.enrich  # background job exists


def test_meaning_search_ranks_sources_by_their_posts(data):
    with SessionLocal() as db:
        semantic._index = None
        r = semantic.search(db, "assessment grading rubric", floor=0.5)
        assert r and r["analysed"] >= 4
        assert [i.title for i, _ in r["posts"]][:1] == ["Assessment and grading with rubrics"]
        assert r["sources"][0][0] == data["source_id"] and r["sources"][0][2] >= 1
        assert not [i for i, _ in r["posts"] if "Hockey" in i.title]


def test_similar_sources_suggests_feeds_outside_the_bundle(data):
    with SessionLocal() as db:
        u = db.query(User).filter_by(email="sem@example.edu").one()
        other = Source(feed_url="https://sem.test/other", title="Other grading blog", added_by_id=u.id)
        db.add(other)
        db.flush()
        db.add(Item(source_id=other.id, guid="o1", url="https://sem.test/o1", title="Rubric design for grading assessment", text="rubric grading assessment"))
        db.add(Item(source_id=other.id, guid="o2", url="https://sem.test/o2", title="Hockey", text="hockey"))
        db.commit()
        semantic.embed_pending(db)
        semantic._index = None
        seed = db.query(Item).filter_by(title="Assessment and grading with rubrics").one()
        r = semantic.similar_sources(db, [seed.id], {data["source_id"]}, floor=0.5)
        assert r and r[0][0] == other.id and r[0][2] == 1  # the grading post, not the hockey one
        assert semantic.similar_sources(db, [], set()) is None


def test_related_posts_fragment(data):
    from fastapi.testclient import TestClient

    from aggrssive import scheduler
    from aggrssive.main import app

    scheduler.start = lambda: None
    scheduler.stop = lambda: None
    with SessionLocal() as db:
        semantic._index = None
        seed = db.query(Item).filter_by(title="Assessment and grading with rubrics").one()
        picks = semantic.related(db, seed, floor=0.5)
        assert picks and picks[0][0].title == "Rubric design for grading assessment"
        assert all(p.id != seed.id for p, _ in picks)
        sid = seed.id
        hockey = db.query(Item).filter_by(title="Hockey season preview").one()
        hockey.embedding = None
        db.commit()
        hid = hockey.id
    c = TestClient(app)
    r = c.get(f"/items/{sid}/related")
    assert r.status_code == 200 and "Rubric design for grading assessment" in r.text
    assert "Not analysed yet" in c.get(f"/items/{hid}/related").text
    assert c.get("/items/999999/related").status_code == 404
