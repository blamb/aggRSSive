"""Filtering: decide which items belong in a bundle.

Rules live on sources (apply wherever that source appears) and on bundles.
Exclude rules always win. Include rules are combined with the bundle's
match_mode: "any" (at least one include rule matches) or "all".
A bundle with no include rules includes everything not excluded.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .models import Bundle, Item, ItemOverride, Rule, utcnow

FIELDS = ("any", "title", "text", "author", "url", "category")


def _haystacks(item: Item, field: str) -> list[str]:
    if field == "title":
        return [item.title]
    if field == "text":
        return [item.text]
    if field == "author":
        return [item.author]
    if field == "url":
        return [item.url]
    if field == "category":
        return item.categories.split("\n") if item.categories else []
    return [item.title, item.text, item.author, item.url, item.categories]


_regex_cache: dict[str, re.Pattern | None] = {}


def _compile(pattern: str) -> re.Pattern | None:
    if pattern not in _regex_cache:
        try:
            _regex_cache[pattern] = re.compile(pattern, re.IGNORECASE)
        except re.error:
            _regex_cache[pattern] = None
    return _regex_cache[pattern]


def rule_matches(rule: Rule, item: Item) -> bool:
    hay = _haystacks(item, rule.field)
    if rule.is_regex:
        rx = _compile(rule.pattern)
        if rx is None:
            return False
        return any(rx.search(h or "") for h in hay)
    needle = rule.pattern.lower()
    return any(needle in (h or "").lower() for h in hay)


def item_passes(item: Item, rules: list[Rule], match_mode: str = "any") -> bool:
    excludes = [r for r in rules if r.kind == "exclude"]
    includes = [r for r in rules if r.kind == "include"]
    if any(rule_matches(r, item) for r in excludes):
        return False
    if not includes:
        return True
    hits = [rule_matches(r, item) for r in includes]
    return all(hits) if match_mode == "all" else any(hits)


@dataclass
class BundleItem:
    item: Item
    pinned: bool = False
    note: str = ""


def _norm_title(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def bundle_items(db: Session, bundle: Bundle, limit: int | None = None, include_hidden: bool = False) -> list[BundleItem]:
    """Resolve a bundle into its current list of items, filtered and curated."""
    source_ids = [s.id for s in bundle.sources if s.is_active]
    if not source_ids:
        return []

    rules = db.execute(select(Rule).where(Rule.owner_type == "bundle", Rule.owner_id == bundle.id)).scalars().all()
    source_rules: dict[int, list[Rule]] = {}
    for r in db.execute(select(Rule).where(Rule.owner_type == "source", Rule.owner_id.in_(source_ids))).scalars():
        source_rules.setdefault(r.owner_id, []).append(r)

    q = select(Item).where(Item.source_id.in_(source_ids)).options(selectinload(Item.source)).order_by(Item.published_at.desc())
    if bundle.max_age_days:
        q = q.where(Item.published_at >= utcnow() - timedelta(days=bundle.max_age_days))
    # Over-fetch so that filtering still leaves us enough.
    cap = limit or bundle.max_items or 50
    q = q.limit(max(cap * 5, 200))

    overrides = {o.item_id: o for o in bundle.overrides}

    out: list[BundleItem] = []
    pinned: list[BundleItem] = []
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    for item in db.execute(q).scalars():
        o = overrides.get(item.id)
        if o and o.hidden and not include_hidden:
            continue
        if not (o and o.pinned):
            if not item_passes(item, source_rules.get(item.source_id, []), "any"):
                continue
            if not item_passes(item, rules, bundle.match_mode):
                continue
        if bundle.dedupe:
            key_u = item.url.rstrip("/").lower()
            key_t = _norm_title(item.title)
            if (key_u and key_u in seen_urls) or (key_t and key_t in seen_titles):
                continue
            seen_urls.add(key_u)
            seen_titles.add(key_t)
        bi = BundleItem(item=item, pinned=bool(o and o.pinned), note=(o.note if o else ""))
        (pinned if bi.pinned else out).append(bi)

    result = pinned + out
    return result[:cap]


def get_override(db: Session, bundle_id: int, item_id: int, create: bool = False) -> ItemOverride | None:
    o = db.execute(select(ItemOverride).where(ItemOverride.bundle_id == bundle_id, ItemOverride.item_id == item_id)).scalar_one_or_none()
    if o is None and create:
        o = ItemOverride(bundle_id=bundle_id, item_id=item_id)
        db.add(o)
    return o
