"""Filtering: decide which items belong in a bundle, and say why.

Rules live on sources (apply wherever that source appears) and on bundles.
Exclude rules always win. Include rules are combined with the bundle's
match_mode: "any" (at least one include rule matches) or "all".
A bundle with no include rules includes everything not excluded.

Rule fields:
  any/title/text/author/url/category  word, phrase or regex matching
  semantic                            "meaning": local-embedding similarity to a description
  ai                                  plain-language rule judged once per item by GenAI
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from . import judge, semantic
from .models import Bundle, Item, ItemOverride, Rule, utcnow

FIELDS = ("any", "title", "text", "author", "url", "category", "semantic", "ai")
FIELD_LABELS = {
    "any": "anywhere",
    "title": "title",
    "text": "text",
    "author": "author",
    "url": "URL",
    "category": "category",
    "semantic": "meaning (local model)",
    "ai": "plain language (GenAI)",
}


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


@dataclass
class Context:
    """What the smarter rules need at match time: cached verdicts for GenAI rules."""

    judgements: dict[tuple[int, int], bool] = field(default_factory=dict)


def rule_matches(rule: Rule, item: Item, ctx: Context | None = None) -> bool | None:
    """True/False, or None when the answer isn't known yet (item not analysed / not judged)."""
    if rule.field == "semantic":
        sim = semantic.similarity(item, rule.pattern)
        if sim is None:
            return None
        return sim >= (rule.threshold if rule.threshold is not None else semantic.STRICTNESS["normal"])
    if rule.field == "ai":
        if ctx is None or (rule.id, item.id) not in ctx.judgements:
            return None
        return ctx.judgements[(rule.id, item.id)]
    hay = _haystacks(item, rule.field)
    if rule.is_regex:
        rx = _compile(rule.pattern)
        if rx is None:
            return False
        return any(rx.search(h or "") for h in hay)
    needle = rule.pattern.lower()
    return any(needle in (h or "").lower() for h in hay)


def describe(rule: Rule) -> str:
    if rule.field == "semantic":
        return f"meaning ≈ “{rule.pattern}” ({semantic.strictness_label(rule.threshold)})"
    if rule.field == "ai":
        return f"GenAI: “{rule.pattern}”"
    return f"{FIELD_LABELS.get(rule.field, rule.field)} {'matches' if rule.is_regex else 'contains'} “{rule.pattern}”"


def evaluate(item: Item, rules: list[Rule], match_mode: str = "any", ctx: Context | None = None) -> tuple[bool, str]:
    """Return (passes, reason). Unknown verdicts count as 'no match': an include rule that can't judge yet
    keeps the item out (pending), an exclude rule that can't judge yet lets it through."""
    excludes = [r for r in rules if r.kind == "exclude"]
    includes = [r for r in rules if r.kind == "include"]
    for r in excludes:
        if rule_matches(r, item, ctx):
            return False, f"excluded: {describe(r)}"
    if not includes:
        return True, "no include rules"
    results = [(r, rule_matches(r, item, ctx)) for r in includes]
    if match_mode == "all":
        if all(v for _, v in results):
            return True, "matches all include rules"
        missing = next(r for r, v in results if not v)
        pending = any(v is None for _, v in results)
        return False, ("pending: " if pending else "doesn't match: ") + describe(missing)
    hit = next((r for r, v in results if v), None)
    if hit:
        return True, f"included: {describe(hit)}"
    if any(v is None for _, v in results):
        return False, "pending: not analysed yet"
    return False, "no include rule matches"


def item_passes(item: Item, rules: list[Rule], match_mode: str = "any", ctx: Context | None = None) -> bool:
    return evaluate(item, rules, match_mode, ctx)[0]


@dataclass
class BundleItem:
    item: Item
    pinned: bool = False
    note: str = ""
    reason: str = ""


def _norm_title(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def _load_rules(db: Session, bundle: Bundle, source_ids: list[int]) -> tuple[list[Rule], dict[int, list[Rule]]]:
    rules = db.execute(select(Rule).where(Rule.owner_type == "bundle", Rule.owner_id == bundle.id)).scalars().all()
    source_rules: dict[int, list[Rule]] = {}
    for r in db.execute(select(Rule).where(Rule.owner_type == "source", Rule.owner_id.in_(source_ids))).scalars():
        source_rules.setdefault(r.owner_id, []).append(r)
    return rules, source_rules


def _context(db: Session, items: list[Item], rules: list[Rule], source_rules: dict[int, list[Rule]]) -> Context:
    """Load cached GenAI verdicts for these items; judge a small batch of unjudged ones right now if we can."""
    ai_rules = [r for r in rules if r.field == "ai"] + [r for rs in source_rules.values() for r in rs if r.field == "ai"]
    ctx = Context()
    if not ai_rules or not items:
        return ctx
    item_ids = [i.id for i in items]
    ctx.judgements = judge.judgements_for(db, [r.id for r in ai_rules], item_ids)
    if judge.enabled():
        for r in ai_rules:
            applicable = items if r.owner_type == "bundle" else [i for i in items if i.source_id == r.owner_id]
            unjudged = [i for i in applicable if (r.id, i.id) not in ctx.judgements]
            if unjudged:
                for iid, v in judge.judge_items(db, r, unjudged[: judge.BATCH]).items():
                    ctx.judgements[(r.id, iid)] = v
    return ctx


def resolve(db: Session, bundle: Bundle, limit: int | None = None, include_hidden: bool = False, with_excluded: bool = False) -> tuple[list[BundleItem], list[BundleItem]]:
    """Resolve a bundle into (included, excluded) lists with reasons. `excluded` is only filled when asked."""
    source_ids = [s.id for s in bundle.sources if s.is_active]
    if not source_ids:
        return [], []
    rules, source_rules = _load_rules(db, bundle, source_ids)

    q = select(Item).where(Item.source_id.in_(source_ids)).options(selectinload(Item.source)).order_by(Item.published_at.desc())
    if bundle.max_age_days:
        q = q.where(Item.published_at >= utcnow() - timedelta(days=bundle.max_age_days))
    cap = limit or bundle.max_items or 50
    candidates = db.execute(q.limit(max(cap * 5, 200))).scalars().all()
    ctx = _context(db, candidates, rules, source_rules)
    overrides = {o.item_id: o for o in bundle.overrides}

    included: list[BundleItem] = []
    pinned: list[BundleItem] = []
    excluded: list[BundleItem] = []
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    for item in candidates:
        o = overrides.get(item.id)
        if o and o.hidden and not include_hidden:
            if with_excluded:
                excluded.append(BundleItem(item=item, reason="hidden by you"))
            continue
        if o and o.pinned:
            pinned.append(BundleItem(item=item, pinned=True, note=o.note, reason="pinned"))
            continue
        ok, why = evaluate(item, source_rules.get(item.source_id, []), "any", ctx)
        if ok:
            ok, why = evaluate(item, rules, bundle.match_mode, ctx)
        if not ok:
            if with_excluded:
                excluded.append(BundleItem(item=item, reason=why))
            continue
        if bundle.dedupe:
            key_u = item.url.rstrip("/").lower()
            key_t = _norm_title(item.title)
            if (key_u and key_u in seen_urls) or (key_t and key_t in seen_titles):
                if with_excluded:
                    excluded.append(BundleItem(item=item, reason="duplicate"))
                continue
            seen_urls.add(key_u)
            seen_titles.add(key_t)
        included.append(BundleItem(item=item, note=(o.note if o else ""), reason=why))
    return (pinned + included)[:cap], excluded


def bundle_items(db: Session, bundle: Bundle, limit: int | None = None, include_hidden: bool = False) -> list[BundleItem]:
    """Resolve a bundle into its current list of items, filtered and curated."""
    return resolve(db, bundle, limit, include_hidden)[0]


def get_override(db: Session, bundle_id: int, item_id: int, create: bool = False) -> ItemOverride | None:
    o = db.execute(select(ItemOverride).where(ItemOverride.bundle_id == bundle_id, ItemOverride.item_id == item_id)).scalar_one_or_none()
    if o is None and create:
        o = ItemOverride(bundle_id=bundle_id, item_id=item_id)
        db.add(o)
    return o
