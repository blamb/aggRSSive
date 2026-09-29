"""Portable bundles: export one (or all of yours) as a JSON file; import it on any aggRSSive install.

The file carries everything a bundle is made of: its settings, its sources with their tags and classification
(bookmark lists travel with their bookmarks, since they exist nowhere else), its rules, and its curation
(pins, hides, notes) keyed by item address. Importing re-creates the bundle privately for the importer,
re-uses sources the site already has, and applies curation to items as they turn up.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import classification
from .config import get_settings
from .models import Bundle, Item, ItemOverride, Rule, Source, Tag, User, aware, utcnow

FORMAT_ONE = "aggrssive-bundle/1"
FORMAT_MANY = "aggrssive-bundles/1"
FEEDLESS = ("bookmarks", "page", "pagediff")


def export_bundle(db: Session, b: Bundle) -> dict:
    rules = db.execute(select(Rule).where(Rule.owner_type == "bundle", Rule.owner_id == b.id).order_by(Rule.id)).scalars().all()
    by_id = {i.id: i for i in db.execute(select(Item).where(Item.id.in_([o.item_id for o in b.overrides]))).scalars()} if b.overrides else {}
    return {
        "format": FORMAT_ONE,
        "exported_at": utcnow().isoformat(),
        "from": f"{get_settings().base_url}/bundles/{b.slug}",
        "bundle": {
            "title": b.title,
            "description": b.description,
            "is_public": b.is_public,
            "match_mode": b.match_mode,
            "max_age_days": b.max_age_days,
            "max_items": b.max_items,
            "dedupe": b.dedupe,
            "all_sources": b.all_sources,
        },
        "sources": [_export_source(db, s) for s in b.sources],
        "rules": [{"kind": r.kind, "field": r.field, "pattern": r.pattern, "is_regex": r.is_regex, "threshold": r.threshold} for r in rules],
        "curation": [
            {"url": by_id[o.item_id].url, "title": by_id[o.item_id].title, "pinned": o.pinned, "hidden": o.hidden, "note": o.note}
            for o in b.overrides
            if o.item_id in by_id and (o.pinned or o.hidden or o.note)
        ],
    }


def _export_source(db: Session, s: Source) -> dict:
    d = {
        "feed_url": s.feed_url,
        "title": s.title,
        "site_url": s.site_url,
        "description": s.description,
        "kind": s.kind,
        "tags": [t.name for t in s.tags],
        "categories": [classification.key(c) for c in s.categories],
    }
    if s.kind == "bookmarks":  # the list is the content; nothing else has it
        d["items"] = [
            {"url": i.url, "title": i.title, "summary": i.summary, "author": i.author, "image_url": i.image_url, "categories": i.categories, "published_at": aware(i.published_at).isoformat() if i.published_at else None}
            for i in db.execute(select(Item).where(Item.source_id == s.id).order_by(Item.published_at.desc())).scalars()
        ]
    return d


def export_all(db: Session, user: User) -> dict:
    bundles = db.execute(select(Bundle).where(Bundle.owner_id == user.id).order_by(Bundle.title)).scalars().all()
    return {"format": FORMAT_MANY, "exported_at": utcnow().isoformat(), "from": get_settings().base_url, "bundles": [export_bundle(db, b) for b in bundles]}


def parse(data: bytes) -> list[dict]:
    """One or many bundle documents from a file. Raises ValueError with a plain message."""
    try:
        doc = json.loads(data)
    except ValueError as e:
        raise ValueError(f"not JSON: {e}") from e
    if not isinstance(doc, dict):
        raise ValueError("not an aggRSSive export")
    if doc.get("format") == FORMAT_ONE:
        return [doc]
    if doc.get("format") == FORMAT_MANY and isinstance(doc.get("bundles"), list):
        return [b for b in doc["bundles"] if isinstance(b, dict) and b.get("format") == FORMAT_ONE]
    raise ValueError("not an aggRSSive export (unknown format)")


def _slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40] or "list"


def _tag(db: Session, name: str) -> Tag | None:
    name = name.strip().lower().lstrip("#")[:80]
    if not name:
        return None
    t = db.execute(select(Tag).where(Tag.name == name)).scalar_one_or_none()
    if t is None:
        t = Tag(name=name)
        db.add(t)
        db.flush()
    return t


def _import_source(db: Session, d: dict, user: User) -> Source | None:
    feed_url = str(d.get("feed_url", ""))[:2048]
    kind = d.get("kind") or "feed"
    if kind == "bookmarks":
        title = str(d.get("title") or "Bookmarks")[:200]
        base = f"bookmarks://{user.id}/{_slugify(title)}"
        url, n = base, 2
        while db.execute(select(Source).where(Source.feed_url == url)).scalar_one_or_none():
            url = f"{base}-{n}"
            n += 1
        s = Source(feed_url=url, title=title, description=str(d.get("description") or "")[:2000], kind="bookmarks", added_by_id=user.id, last_success_at=utcnow())
        db.add(s)
        db.flush()
        for it in d.get("items", []) or []:
            u = str(it.get("url", ""))[:2048]
            if not u:
                continue
            when = None
            if it.get("published_at"):
                try:
                    when = datetime.fromisoformat(it["published_at"])
                    when = when if when.tzinfo else when.replace(tzinfo=timezone.utc)
                except ValueError:
                    when = None
            db.add(Item(source_id=s.id, guid=u, url=u, title=str(it.get("title") or u)[:1000], summary=str(it.get("summary") or ""), author=str(it.get("author") or "")[:255], image_url=(it.get("image_url") or None), categories=str(it.get("categories") or ""), text=str(it.get("title") or "")[:20000], published_at=when or utcnow()))
    else:
        if not feed_url or feed_url.startswith("bookmarks://"):
            return None
        s = db.execute(select(Source).where(Source.feed_url == feed_url)).scalar_one_or_none()
        if s is None:
            s = Source(feed_url=feed_url, title=str(d.get("title") or "")[:500], site_url=(d.get("site_url") or None), description=str(d.get("description") or "")[:2000], kind=kind if kind in ("page", "pagediff") else "feed", added_by_id=user.id)
            db.add(s)
            db.flush()
    for name in d.get("tags", []) or []:
        t = _tag(db, str(name))
        if t and t not in s.tags:
            s.tags.append(t)
    for k in d.get("categories", []) or []:
        c = classification.get(db, str(k))
        if c and c not in s.categories:
            s.categories.append(c)
    return s


def import_bundle(db: Session, doc: dict, user: User) -> tuple[Bundle, list[int]]:
    """Create the bundle for `user`, privately. Returns (bundle, ids of newly created sources to fetch)."""
    from .routes.bundles import _set_sources

    meta = doc.get("bundle", {}) or {}
    b = Bundle(
        owner_id=user.id,
        title=str(meta.get("title") or "Imported bundle")[:300],
        description=str(meta.get("description") or "")[:5000],
        is_public=False,
        match_mode="all" if meta.get("match_mode") == "all" else "any",
        max_age_days=int(meta["max_age_days"]) if str(meta.get("max_age_days") or "").isdigit() else None,
        max_items=max(1, min(int(meta.get("max_items") or 50), 500)),
        dedupe=bool(meta.get("dedupe", True)),
        all_sources=bool(meta.get("all_sources", False)),
    )
    db.add(b)
    db.flush()
    before = {s.id for s in db.execute(select(Source)).scalars()}
    sources = [s for s in (_import_source(db, d, user) for d in doc.get("sources", []) or [] if isinstance(d, dict)) if s is not None]
    _set_sources(db, b, [s.id for s in sources])
    for r in doc.get("rules", []) or []:
        if not isinstance(r, dict) or r.get("kind") not in ("include", "exclude") or not r.get("pattern"):
            continue
        db.add(Rule(owner_type="bundle", owner_id=b.id, kind=r["kind"], field=str(r.get("field") or "any")[:16], pattern=str(r["pattern"])[:1000], is_regex=bool(r.get("is_regex")), threshold=float(r["threshold"]) if r.get("threshold") is not None else None))
    b.pending_curation = json.dumps([c for c in (doc.get("curation", []) or []) if isinstance(c, dict) and c.get("url")])
    apply_pending_curation(db, b)
    db.commit()
    new_ids = [s.id for s in sources if s.id not in before and s.kind not in FEEDLESS]
    return b, new_ids


def apply_pending_curation(db: Session, b: Bundle) -> int:
    """Pins, hides and notes from an import, applied to items as they exist. Returns how many were applied."""
    if not b.pending_curation:
        return 0
    try:
        pending = json.loads(b.pending_curation)
    except ValueError:
        b.pending_curation = None
        return 0
    if not pending:
        b.pending_curation = None
        return 0
    source_ids = [s.id for s in b.sources]
    urls = [c["url"] for c in pending]
    found = {i.url: i for i in db.execute(select(Item).where(Item.source_id.in_(source_ids), Item.url.in_(urls))).scalars()} if source_ids else {}
    left, applied = [], 0
    for c in pending:
        item = found.get(c["url"])
        if item is None:
            left.append(c)
            continue
        o = db.execute(select(ItemOverride).where(ItemOverride.bundle_id == b.id, ItemOverride.item_id == item.id)).scalar_one_or_none()
        if o is None:
            o = ItemOverride(bundle_id=b.id, item_id=item.id)
            db.add(o)
        o.pinned, o.hidden, o.note = bool(c.get("pinned")), bool(c.get("hidden")), str(c.get("note") or "")[:2000]
        applied += 1
    b.pending_curation = json.dumps(left) if left else None
    db.commit()
    return applied
