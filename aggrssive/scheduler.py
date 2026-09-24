"""Background polling. Runs inside the web process; no extra services."""

from __future__ import annotations

import logging
from datetime import timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from .config import get_settings
from .db import SessionLocal
from .feeds.fetch import fetch_source
from .models import Source, utcnow

log = logging.getLogger("aggrssive.scheduler")
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
            if s.last_fetched_at and now - s.last_fetched_at < backoff:
                continue
            try:
                n = fetch_source(db, s)
                if n:
                    log.info("%s: %d new", s.title or s.feed_url, n)
            except Exception:  # keep the loop alive whatever happens
                log.exception("fetch failed for %s", s.feed_url)
                db.rollback()


def fetch_one(source_id: int) -> None:
    with SessionLocal() as db:
        s = db.get(Source, source_id)
        if s:
            fetch_source(db, s)


def start() -> None:
    settings = get_settings()
    scheduler.add_job(poll_all, "interval", minutes=max(1, settings.poll_interval_minutes // 3), id="poll", replace_existing=True, next_run_time=utcnow() + timedelta(seconds=10))
    scheduler.start()


def stop() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)


def fetch_soon(source_id: int) -> None:
    """Fetch a single source in the background, right away."""
    scheduler.add_job(fetch_one, args=[source_id], id=f"fetch-{source_id}", replace_existing=True)
