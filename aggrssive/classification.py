"""Controlled classification of sources, alongside the free tags.

Two frameworks ship as data files in aggrssive/data/: the Library of Congress Classification outline
(classes and subclasses) and UNESCO's ISCED-F 2013 fields of education and training. They are seeded
into the categories table on startup. Assignments are proposals until a person accepts them.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import get_settings
from .models import Category, Item, Source

log = logging.getLogger("aggrssive.classification")
DATA = Path(__file__).parent / "data"

FRAMEWORKS = {
    "lcc": {"title": "Library of Congress Classification", "short": "LCC", "file": "lcc.txt", "levels": ("class", "subclass")},
    "isced": {"title": "ISCED-F 2013 fields of education", "short": "ISCED-F", "file": "isced_f_2013.txt", "levels": ("broad field", "narrow field", "detailed field")},
}


@dataclass
class Node:
    framework: str
    code: str
    label: str
    hints: str
    depth: int
    parent: str | None


def _parent(framework: str, code: str, known: set[str]) -> str | None:
    if framework == "lcc":
        # Every subclass (DA, DAW, KBM...) hangs directly off its single-letter class in the outline.
        return None if len(code) == 1 else code[0]
    if len(code) <= 2:
        return None
    return code[:-1]


@lru_cache
def load(framework: str) -> list[Node]:
    lines = (DATA / FRAMEWORKS[framework]["file"]).read_text(encoding="utf-8").splitlines()
    raw = [ln.split("|") for ln in lines if ln.strip() and not ln.startswith("#")]
    known = {r[0].strip() for r in raw}
    out = []
    for parts in raw:
        code = parts[0].strip()
        label = parts[1].strip()
        hints = parts[2].strip() if len(parts) > 2 else ""
        parent = _parent(framework, code, known)
        depth = 0
        p = parent
        while p:
            depth += 1
            p = _parent(framework, p, known)
        out.append(Node(framework, code, label, hints, depth, parent))
    return out


def seed(db: Session) -> int:
    """Insert any framework nodes missing from the database. Idempotent."""
    added = 0
    for fw in FRAMEWORKS:
        existing = {c for (c,) in db.execute(select(Category.code).where(Category.framework == fw))}
        for pos, n in enumerate(load(fw)):
            if n.code not in existing:
                db.add(Category(framework=fw, code=n.code, label=n.label, parent_code=n.parent, depth=n.depth, position=pos))
                added += 1
    db.commit()
    return added


def key(c: Category) -> str:
    return f"{c.framework}:{c.code}"


def parse_key(k: str) -> tuple[str, str] | None:
    if ":" not in k:
        return None
    fw, code = k.split(":", 1)
    fw, code = fw.strip().lower(), code.strip().upper()
    return (fw, code) if fw in FRAMEWORKS and code else None


def get(db: Session, k: str) -> Category | None:
    p = parse_key(k)
    if not p:
        return None
    return db.execute(select(Category).where(Category.framework == p[0], Category.code == p[1])).scalar_one_or_none()


def ancestors(db: Session, c: Category) -> list[Category]:
    out = []
    while c.parent_code:
        c = db.execute(select(Category).where(Category.framework == c.framework, Category.code == c.parent_code)).scalar_one_or_none()
        if not c:
            break
        out.append(c)
    return list(reversed(out))


def tree(db: Session, framework: str) -> list[tuple[Category, int]]:
    """All nodes of a framework in outline order, with the number of sources under each (descendants included)."""
    from .models import source_categories

    nodes = db.execute(select(Category).where(Category.framework == framework).order_by(Category.position)).scalars().all()
    direct = dict(db.execute(select(source_categories.c.category_id, func.count(source_categories.c.source_id)).group_by(source_categories.c.category_id)).all())
    by_code = {n.code: n for n in nodes}
    counts: dict[str, int] = {n.code: direct.get(n.id, 0) for n in nodes}
    # Roll direct counts up to every ancestor (approximate: a source under two children counts twice).
    for n in nodes:
        p = n.parent_code
        while p and p in by_code:
            counts[p] += direct.get(n.id, 0)
            p = by_code[p].parent_code
    return [(n, counts[n.code]) for n in nodes]


def sources_under(db: Session, c: Category) -> list[Source]:
    """Sources assigned to this node or any node beneath it."""
    q = (
        select(Source)
        .join(Source.categories)
        .where(Category.framework == c.framework, Category.code.like(c.code + "%"))
        .distinct()
        .order_by(Source.title)
    )
    return db.execute(q).scalars().all()


def search(db: Session, q: str, limit: int = 30) -> list[Category]:
    q = q.strip()
    if not q:
        return []
    like = f"%{q}%"
    return db.execute(select(Category).where((Category.label.ilike(like)) | (Category.code.ilike(q + "%"))).order_by(Category.framework, Category.position).limit(limit)).scalars().all()


# --- Suggestions ------------------------------------------------------------


def _lines(s: str | None) -> list[str]:
    return [x for x in (s or "").split("\n") if x]


def _framework_prompt() -> str:
    parts = []
    for fw, meta in FRAMEWORKS.items():
        parts.append(f"## {meta['title']} (framework id: {fw})")
        for n in load(fw):
            hint = f"  [{n.hints}]" if n.hints else ""
            parts.append(f"{'  ' * n.depth}{n.code} {n.label}{hint}")
    return "\n".join(parts)


def ai_suggestions(db: Session, source: Source) -> list[str]:
    """Ask the model for 1-3 codes per framework. Returns 'framework:code' keys."""
    settings = get_settings()
    if not settings.ai_enabled:
        return []
    import anthropic

    items = db.execute(select(Item).where(Item.source_id == source.id).order_by(Item.published_at.desc()).limit(15)).scalars().all()
    system = (
        "You classify a web feed (a blog, journal, news source, podcast...) into two library classification frameworks, "
        "so that educators can browse a shared collection by discipline. Choose the most specific node that fits the feed's "
        "main subject; prefer subclasses/detailed fields over top-level classes. Choose 1 to 3 codes per framework, best first. "
        "If the feed is about teaching or learning in a discipline, include an Education code as well as the discipline. "
        'Reply with JSON only: {"lcc": ["LB", ...], "isced": ["0111", ...]}.\n\n' + _framework_prompt()
    )
    user = (
        f"Feed title: {source.title}\nDescription: {source.description[:500]}\nSite: {source.site_url or source.feed_url}\n"
        f"Tags people gave it: {', '.join(t.name for t in source.tags) or '(none)'}\n"
        "Recent item titles:\n" + "\n".join(f"- {i.title[:150]}" for i in items)
    )
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    try:
        resp = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=200,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],  # the frameworks are the same every call
            messages=[{"role": "user", "content": user}],
        )
    except anthropic.APIStatusError as e:
        log.warning("classification suggestion failed (%s): %s", e.status_code, e.message)
        return []
    except anthropic.APIConnectionError as e:
        log.warning("classification suggestion: network error: %s", e)
        return []
    text = "".join(b.text for b in resp.content if b.type == "text")
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    out: list[str] = []
    for fw in FRAMEWORKS:
        valid = {n.code for n in load(fw)}
        for code in (data.get(fw) or [])[:3]:
            code = str(code).strip().upper()
            if code in valid:
                out.append(f"{fw}:{code}")
    return out


def refresh_suggestions(db: Session, source: Source, use_ai: bool = True) -> list[str]:
    have = {key(c) for c in source.categories}
    rejected = set(_lines(source.rejected_categories))
    proposed: list[str] = []
    for k in (ai_suggestions(db, source) if use_ai else []) + _lines(source.suggested_categories):
        if k not in have and k not in rejected and k not in proposed and get(db, k):
            proposed.append(k)
    source.suggested_categories = "\n".join(proposed[:6])
    db.commit()
    return proposed[:6]


def decide(db: Session, source: Source, k: str, accept: bool) -> None:
    p = parse_key(k)
    if not p:
        return
    k = f"{p[0]}:{p[1]}"
    source.suggested_categories = "\n".join(x for x in _lines(source.suggested_categories) if x != k)
    if accept:
        c = get(db, k)
        if c and c not in source.categories:
            source.categories.append(c)
    else:
        rej = _lines(source.rejected_categories)
        if k not in rej:
            source.rejected_categories = "\n".join(rej + [k])
    db.commit()
