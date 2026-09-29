"""Tag suggestions for sources. Suggestions are proposals: a person accepts, edits or rejects each one.

Two layers:
- heuristic: free and automatic. Existing vocabulary found in the feed's text, plus categories the feed declares.
- ai: opt-in, on demand. Claude proposes tags, preferring the vocabulary people already use here.
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .models import Item, Source, Tag

log = logging.getLogger("aggrssive.tagging")

GENERIC = {"uncategorized", "uncategorised", "general", "misc", "miscellaneous", "blog", "posts", "post", "articles", "article", "featured", "news", "home"}
MAX_SUGGESTIONS = 5


def _lines(s: str | None) -> list[str]:
    return [x for x in (s or "").split("\n") if x]


def normalize(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower().lstrip("#"))[:80]


def _recent_items(db: Session, source: Source, n: int = 40) -> list[Item]:
    return db.execute(select(Item).where(Item.source_id == source.id).order_by(Item.published_at.desc()).limit(n)).scalars().all()


def heuristic_suggestions(db: Session, source: Source) -> list[str]:
    items = _recent_items(db, source)
    text = " ".join([source.title, source.description] + [i.title for i in items]).lower()
    vocab = [t.name for t in db.execute(select(Tag)).scalars()]

    scored: Counter[str] = Counter()
    for name in vocab:
        if len(name) < 3:
            continue
        hits = len(re.findall(r"\b" + re.escape(name) + r"\b", text))
        if hits:
            scored[name] += hits * 2  # vocabulary matches count double: they're what makes the collection browsable

    cats: Counter[str] = Counter()
    for i in items:
        for c in _lines(i.categories):
            c = normalize(c)
            if 2 < len(c) <= 30 and c not in GENERIC:
                cats[c] += 1
    threshold = 2 if len(items) >= 5 else 1
    for c, n in cats.items():
        if n >= threshold:
            scored[c] += n

    return [name for name, _ in scored.most_common(MAX_SUGGESTIONS * 2)]


def ai_suggestions(db: Session, source: Source) -> list[str]:
    settings = get_settings()
    if not settings.ai_enabled:
        return []
    import anthropic

    items = _recent_items(db, source, 15)
    vocab = sorted({t.name for t in db.execute(select(Tag)).scalars()})[:200]
    prompt = (
        "You suggest tags for a feed in a shared, educator-run collection of feeds (aggRSSive). "
        "Tags are short lowercase phrases describing the feed's subject and kind (e.g. 'open education', 'edtech', 'podcast', 'research'). "
        "Reuse existing vocabulary whenever it fits; invent a new tag only when nothing existing describes the feed. "
        "Suggest 3 to 6 tags. Reply with a JSON array of strings and nothing else.\n\n"
        f"Existing vocabulary: {json.dumps(vocab)}\n\n"
        f"Feed title: {source.title}\nFeed description: {source.description[:500]}\nSite: {source.site_url or source.feed_url}\n"
        "Recent item titles:\n" + "\n".join(f"- {i.title[:150]}" for i in items)
    )
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    try:
        resp = client.messages.create(model=settings.anthropic_model, max_tokens=256, messages=[{"role": "user", "content": prompt}])
    except anthropic.APIStatusError as e:
        log.warning("Claude tag suggestion failed (%s): %s", e.status_code, e.message)
        return []
    except anthropic.APIConnectionError as e:
        log.warning("Claude tag suggestion: network error: %s", e)
        return []
    text = "".join(b.text for b in resp.content if b.type == "text")
    m = re.search(r"\[.*\]", text, re.S)
    if not m:
        return []
    try:
        tags = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    return [normalize(t) for t in tags if isinstance(t, str) and normalize(t)]


def refresh_suggestions(db: Session, source: Source, use_ai: bool = False) -> list[str]:
    """Recompute pending suggestions for a source. Never applies anything."""
    have = {t.name for t in source.tags}
    rejected = set(_lines(source.rejected_tags))
    proposed: list[str] = []
    for name in heuristic_suggestions(db, source) + (ai_suggestions(db, source) if use_ai else []):
        if name and name not in have and name not in rejected and name not in proposed:
            proposed.append(name)
    # Keep earlier AI suggestions the person hasn't decided on yet.
    for name in _lines(source.suggested_tags):
        if name not in have and name not in rejected and name not in proposed:
            proposed.append(name)
    source.suggested_tags = "\n".join(proposed[:MAX_SUGGESTIONS])
    db.commit()
    return proposed[:MAX_SUGGESTIONS]


def decide(db: Session, source: Source, name: str, accept: bool) -> None:
    name = normalize(name)
    pending = [t for t in _lines(source.suggested_tags) if t != name]
    source.suggested_tags = "\n".join(pending)
    if accept:
        t = db.execute(select(Tag).where(Tag.name == name)).scalar_one_or_none()
        if t is None:
            t = Tag(name=name)
            db.add(t)
            db.flush()
        if t not in source.tags:
            source.tags.append(t)
    else:
        rejected = _lines(source.rejected_tags)
        if name not in rejected:
            source.rejected_tags = "\n".join(rejected + [name])
    db.commit()


def sources_for_tag(db: Session, tag: Tag, limit: int = 10) -> list[dict]:
    """Sources not yet carrying this tag that probably should: by name, by what they publish, by company they keep.

    Each result is {"source", "reasons", "score"}. Sources whose owner rejected this tag are left out for good.
    """
    from sqlalchemy import or_

    from . import semantic
    from .models import source_tags

    name = tag.name
    tagged = db.execute(select(Source).join(source_tags, Source.id == source_tags.c.source_id).where(source_tags.c.tag_id == tag.id)).scalars().all()
    tagged_ids = {s.id for s in tagged}
    found: dict[int, dict] = {}

    def add(src: Source, reason: str, score: float) -> None:
        if src.id in tagged_ids or name in _lines(src.rejected_tags):
            return
        row = found.setdefault(src.id, {"source": src, "reasons": [], "score": 0.0})
        row["reasons"].append(reason)
        row["score"] += score

    like = f"%{name}%"
    for src in db.execute(select(Source).where(Source.is_active.is_(True), or_(Source.title.ilike(like), Source.description.ilike(like)))).scalars():
        add(src, "the name or description mentions it", 2.0)

    # Posts that use the words. A tag is usually a name or a short phrase, and for those the words
    # themselves are the reliable signal; meaning similarity on two words is vague.
    from sqlalchemy import func

    mentions = db.execute(
        select(Item.source_id, func.count(Item.id)).where(or_(Item.title.ilike(like), Item.text.ilike(like))).group_by(Item.source_id)
    ).all()
    for sid, n in mentions:
        if n >= 2:
            src = db.get(Source, sid)
            if src is not None and src.is_active:
                add(src, f"{n} post{'s' if n != 1 else ''} mention it", 1.0 + min(n, 30) / 10)

    # Meaning, only when it is unambiguous: strict threshold and several posts.
    hit = semantic.search(db, name, limit=1, source_limit=40, floor=semantic.STRICTNESS["strict"])
    if hit:
        for sid, score, hits in hit["sources"]:
            src = db.get(Source, sid)
            if src is not None and hits >= 3:
                add(src, f"{hits} posts close in meaning", 0.5 + min(hits, 10) / 10)

    # Company: other tags the tagged sources carry, and who else carries several of them.
    company: Counter[str] = Counter(t.name for s in tagged for t in s.tags if t.id != tag.id)
    if company and len(tagged) >= 2:
        names = [n for n, c in company.most_common(12) if c >= max(2, len(tagged) // 4)]
        if names:
            shared: dict[int, list[str]] = {}
            for src in db.execute(select(Source).join(source_tags, Source.id == source_tags.c.source_id).join(Tag, Tag.id == source_tags.c.tag_id).where(Tag.name.in_(names), Source.is_active.is_(True))).scalars().unique():
                mine = [t.name for t in src.tags if t.name in names]
                if len(mine) >= 2:
                    shared[src.id] = mine
            for sid, mine in shared.items():
                add(db.get(Source, sid), "shares tags: " + ", ".join(sorted(mine)[:4]), 0.6 * len(mine))

    return sorted(found.values(), key=lambda r: -r["score"])[:limit]
