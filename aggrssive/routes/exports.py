"""Feeds and OPML for things that are not bundles: a tag, a heading, the whole collection, one source.

Every list of sources on the site can leave as OPML, and every source can be followed as RSS through
aggRSSive, which is the only way to subscribe to a bookmark list or a watched page.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import classification
from ..config import get_settings
from ..db import get_db
from ..feeds.opml import OpmlEntry, render_opml
from ..models import Item, Source, Tag, source_tags
from .outputs import rss_document

router = APIRouter()
settings = get_settings()

FEEDLESS = ("bookmarks", "page", "pagediff")


def export_feed_url(s: Source) -> str:
    """What to put in OPML for a source: its own feed, or aggRSSive's feed of it when it has none."""
    return f"{settings.base_url}/sources/{s.id}/feed.rss" if s.kind in FEEDLESS else s.feed_url


def _opml(title: str, sources, filename: str) -> Response:
    entries = [OpmlEntry(feed_url=export_feed_url(s), title=s.title or s.feed_url, site_url=s.site_url, folders=[t.name for t in s.tags]) for s in sources]
    return Response(render_opml(title, entries, by_folder=True), media_type="text/x-opml", headers={"Content-Disposition": f'attachment; filename="{filename}.opml"', "Cache-Control": "public, max-age=300"})


@router.get("/sources.opml")
def all_sources_opml(db: Session = Depends(get_db)):
    sources = db.execute(select(Source).where(Source.is_active.is_(True)).options(selectinload(Source.tags)).order_by(Source.title)).scalars().all()
    return _opml("aggRSSive: all sources", sources, "aggrssive-sources")


@router.get("/tags/{name}.opml")
def tag_opml(name: str, db: Session = Depends(get_db)):
    t = db.execute(select(Tag).where(Tag.name == name)).scalar_one_or_none()
    if not t:
        raise HTTPException(404, "No such tag")
    sources = db.execute(select(Source).join(source_tags, Source.id == source_tags.c.source_id).where(source_tags.c.tag_id == t.id).options(selectinload(Source.tags)).order_by(Source.title)).scalars().all()
    return _opml(f"aggRSSive: {t.name}", sources, f"aggrssive-{t.name.replace(' ', '-')}")


@router.get("/classification/{framework}/{code}.opml")
def heading_opml(framework: str, code: str, db: Session = Depends(get_db)):
    c = classification.get(db, f"{framework}:{code}")
    if not c:
        raise HTTPException(404, "No such heading")
    sources = classification.sources_under(db, c)
    for s in sources:
        s.tags  # loaded for folders
    return _opml(f"aggRSSive: {c.code} {c.label}", sources, f"aggrssive-{c.framework}-{c.code}")


@router.get("/sources/{source_id}/feed.rss")
def source_feed(source_id: int, n: int = 50, db: Session = Depends(get_db)):
    s = db.get(Source, source_id)
    if not s:
        raise HTTPException(404, "No such source")
    items = db.execute(select(Item).where(Item.source_id == s.id).options(selectinload(Item.source)).order_by(Item.published_at.desc()).limit(max(1, min(n, 200)))).scalars().all()
    link = s.site_url if s.kind in FEEDLESS and s.site_url else f"{settings.base_url}/sources/{s.id}"
    return rss_document(s.title or s.feed_url, link, f"{settings.base_url}/sources/{s.id}/feed.rss", s.description, items)
