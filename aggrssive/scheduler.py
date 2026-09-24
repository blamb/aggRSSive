"""Background polling. Runs inside the web process; no extra services."""

from __future__ import annotations

import logging
from datetime import timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from . import classification, judge, semantic
from .config import get_settings
from .db import SessionLocal
from .feeds.fetch import fetch_source
from .models import Source, aware, utcnow
from .tagging import refresh_suggestions

log = logging.getLogger("aggrssive.scheduler")


def _after_fetch(db, source: Source, new_items: int) -> None:
    # Fresh material, or a source nobody has tagged yet: recompute the free suggestions.
    if new_items or (not source.tags and not source.suggested_tags):
        try:
            refresh_suggestions(db, source)
        except Exception:
            log.exception("tag suggestions failed for %s", source.feed_url)
            db.rollback()
    # The person who added it asked for GenAI proposals: one round of tags and classification, then done.
    if source.ai_pending and get_settings().ai_enabled and source.items:
        try:
            refresh_suggestions(db, source, use_ai=True)
            classification.refresh_suggestions(db, source, use_ai=True)
        except Exception:
            log.exception("GenAI suggestions failed for %s", source.feed_url)
            db.rollback()
        source.ai_pending = False
        db.commit()
scheduler = BackgroundScheduler(timezone="UTC")


def poll_all() -> None:
    """Fetch every active source that is due. Failing sources back off."""
    settings = get_settings()
    interval = timedelta(minutes=settings.poll_interval_minutes)
    with SessionLocal() as db:
        sources = db.execute(select(Source).where(Source.is_active.is_(True))).scalars().all()
        now = utcnow()
        for s in sources:
            backoff = interval * min(2 ** min(s.error_count, 5), 48)  # up to 48x interval
            last = aware(s.last_fetched_at)
            if last and now - last < backoff:
                continue
            try:
                n = fetch_source(db, s)
                if n:
                    log.info("%s: %d new", s.title or s.feed_url, n)
                _after_fetch(db, s, n)
            except Exception:  # keep the loop alive whatever happens
                log.exception("fetch failed for %s", s.feed_url)
                db.rollback()


def enrich() -> None:
    """Background analysis: embed new items for meaning rules; judge new items for plain-language rules."""
    with SessionLocal() as db:
        try:
            n = semantic.embed_pending(db, 300)
            if n:
                log.info("embedded %d items", n)
        except Exception:
            log.exception("embedding pass failed")
            db.rollback()
        try:
            judge.judge_pending(db, max_calls=4)
        except Exception:
            log.exception("judging pass failed")
            db.rollback()


def fetch_one(source_id: int) -> None:
    with SessionLocal() as db:
        s = db.get(Source, source_id)
        if s:
            n = fetch_source(db, s)
            _after_fetch(db, s, n)


def start() -> None:
    settings = get_settings()
    scheduler.add_job(poll_all, "interval", minutes=max(1, settings.poll_interval_minutes // 3), id="poll", replace_existing=True, next_run_time=utcnow() + timedelta(seconds=10))
    scheduler.add_job(enrich, "interval", minutes=3, id="enrich", replace_existing=True, next_run_time=utcnow() + timedelta(seconds=40))
    scheduler.start()


def stop() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)


def fetch_soon(source_id: int) -> None:
    """Fetch a single source in the background, right away."""
    scheduler.add_job(fetch_one, args=[source_id], id=f"fetch-{source_id}", replace_existing=True)
