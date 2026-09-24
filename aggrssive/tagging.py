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
MAX_SUGGESTIONS = 8


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
