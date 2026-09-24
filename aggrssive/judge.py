"""Plain-language rules judged by GenAI: "only items about assessment design; drop job postings".

Each item is judged once per rule and the verdict is kept, so a rule costs roughly a fraction of a cent
per new item. Judging happens in the background after fetches, and on demand (a small batch) when a
bundle is viewed with unjudged items.
"""

from __future__ import annotations

import json
import logging
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .models import Bundle, Item, Judgement, Rule, bundle_sources

log = logging.getLogger("aggrssive.judge")
BATCH = 25

SYSTEM = (
    "You apply a curator's plain-language rule to items from web feeds, one verdict per item. "
    "The rule describes what the curator wants to keep. For each item decide whether it satisfies the rule, "
    "judging from the title and excerpt only; when genuinely unsure, answer false. "
    'Reply with JSON only: an object mapping each item id (as a string) to true or false.'
)


def enabled() -> bool:
    return get_settings().ai_enabled


def judgements_for(db: Session, rule_ids: list[int], item_ids: list[int]) -> dict[tuple[int, int], bool]:
    if not rule_ids or not item_ids:
        return {}
    rows = db.execute(select(Judgement).where(Judgement.rule_id.in_(rule_ids), Judgement.item_id.in_(item_ids))).scalars()
    return {(j.rule_id, j.item_id): j.passes for j in rows}


def judge_items(db: Session, rule: Rule, items: list[Item]) -> dict[int, bool]:
    """Judge up to BATCH items against one rule in a single request; store and return the verdicts."""
    if not enabled() or not items:
        return {}
    import anthropic

    items = items[:BATCH]
    settings = get_settings()
    listing = "\n\n".join(f"[{i.id}] {i.title[:150]}\nSource: {i.source.title if i.source else ''}\n{i.text[:400]}" for i in items)
    user = f"Rule: {rule.pattern}\n\nItems:\n\n{listing}\n\nReturn JSON: {{\"<id>\": true|false, ...}} for every item id listed."
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    try:
        resp = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=400,
            system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
        )
    except anthropic.APIStatusError as e:
        log.warning("judging failed (%s): %s", e.status_code, e.message)
        return {}
    except anthropic.APIConnectionError as e:
        log.warning("judging: network error: %s", e)
        return {}
    text = "".join(b.text for b in resp.content if b.type == "text")
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return {}
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}
    verdicts: dict[int, bool] = {}
    for i in items:
        v = data.get(str(i.id))
        if isinstance(v, bool):
            verdicts[i.id] = v
            db.add(Judgement(rule_id=rule.id, item_id=i.id, passes=v))
    db.commit()
    return verdicts


def _candidate_items(db: Session, rule: Rule, limit: int) -> list[Item]:
    """Recent items the rule applies to that have no verdict yet."""
    if rule.owner_type == "source":
        source_ids = [rule.owner_id]
    else:
        source_ids = [sid for (sid,) in db.execute(select(bundle_sources.c.source_id).where(bundle_sources.c.bundle_id == rule.owner_id))]
    if not source_ids:
        return []
    judged = select(Judgement.item_id).where(Judgement.rule_id == rule.id)
    return db.execute(
        select(Item).where(Item.source_id.in_(source_ids), Item.id.not_in(judged)).order_by(Item.published_at.desc()).limit(limit)
    ).scalars().all()


def judge_pending(db: Session, max_calls: int = 4) -> int:
    """Background pass: for every plain-language rule, judge a batch of unjudged recent items."""
    if not enabled():
        return 0
    calls = 0
    for rule in db.execute(select(Rule).where(Rule.field == "ai")).scalars().all():
        if calls >= max_calls:
            break
        items = _candidate_items(db, rule, BATCH)
        if items:
            judge_items(db, rule, items)
            calls += 1
    return calls
