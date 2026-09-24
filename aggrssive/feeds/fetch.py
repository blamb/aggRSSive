"""Fetch a source, parse it, normalize entries into Items."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import mktime

import feedparser
import httpx
import nh3
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import Item, Source, utcnow
from .http import client

ALLOWED_TAGS = {"a", "p", "br", "em", "strong", "b", "i", "ul", "ol", "li", "blockquote", "code", "pre", "h1", "h2", "h3", "h4", "h5", "h6", "img", "figure", "figcaption", "table", "thead", "tbody", "tr", "td", "th"}
ALLOWED_ATTRS = {"a": {"href", "title"}, "img": {"src", "alt", "title", "width", "height"}}


def sanitize(html: str) -> str:
    if not html:
        return ""
    return nh3.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, link_rel="noopener noreferrer nofollow")


_ws = re.compile(r"\s+")


def to_text(html: str) -> str:
    if not html:
        return ""
    return _ws.sub(" ", nh3.clean(html, tags=set())).strip()


@dataclass
class ParsedEntry:
    guid: str
    url: str
    title: str = ""
    author: str = ""
    summary: str = ""
    content: str = ""
    image_url: str | None = None
    categories: list[str] = field(default_factory=list)
    published_at: datetime | None = None


@dataclass
class ParsedFeed:
    title: str = ""
    description: str = ""
    site_url: str | None = None
    entries: list[ParsedEntry] = field(default_factory=list)


def _dt(struct) -> datetime | None:
    if not struct:
        return None
    try:
        return datetime.fromtimestamp(mktime(struct), tz=timezone.utc)
    except Exception:
        return None


def _first_image(entry, html: str) -> str | None:
    for key in ("media_thumbnail", "media_content"):
        for m in entry.get(key, []) or []:
            u = m.get("url")
            if u and (m.get("medium") in (None, "image") or str(m.get("type", "")).startswith("image")):
                return u
    for enc in entry.get("enclosures", []) or []:
        if str(enc.get("type", "")).startswith("image") and enc.get("href"):
            return enc["href"]
    m = re.search(r'<img[^>]+src="([^"]+)"', html or "")
    return m.group(1) if m else None


def parse_feedparser(body: bytes) -> ParsedFeed:
    p = feedparser.parse(body)
    pf = ParsedFeed(title=p.feed.get("title", ""), description=p.feed.get("subtitle", "") or p.feed.get("description", ""), site_url=p.feed.get("link"))
    for e in p.entries:
        link = e.get("link") or ""
        content_html = ""
        if e.get("content"):
            content_html = e.content[0].get("value", "")
        summary_html = e.get("summary", "") or ""
        guid = e.get("id") or link or hashlib.sha1((e.get("title", "") + summary_html).encode()).hexdigest()
        pf.entries.append(
            ParsedEntry(
                guid=guid,
                url=link,
                title=e.get("title", "") or "",
                author=e.get("author", "") or "",
                summary=sanitize(summary_html),
                content=sanitize(content_html) if content_html and content_html != summary_html else "",
                image_url=_first_image(e, content_html or summary_html),
                categories=[t.get("term", "") for t in e.get("tags", []) or [] if t.get("term")],
                published_at=_dt(e.get("published_parsed") or e.get("updated_parsed")),
            )
        )
    return pf


def parse_jsonfeed(body: bytes) -> ParsedFeed:
    d = json.loads(body)
    pf = ParsedFeed(title=d.get("title", ""), description=d.get("description", ""), site_url=d.get("home_page_url"))
    for e in d.get("items", []):
        html = e.get("content_html", "") or ""
        text = e.get("content_text", "") or ""
        summary = e.get("summary", "") or text[:500]
        published = e.get("date_published") or e.get("date_modified")
        dt = None
        if published:
            try:
                dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
            except ValueError:
                dt = None
        authors = e.get("authors") or ([e["author"]] if e.get("author") else [])
        pf.entries.append(
            ParsedEntry(
                guid=str(e.get("id") or e.get("url")),
                url=e.get("url", ""),
                title=e.get("title", ""),
                author=", ".join(a.get("name", "") for a in authors if a.get("name")),
                summary=sanitize(summary) if summary else "",
                content=sanitize(html) if html else "",
                image_url=e.get("image") or e.get("banner_image"),
                categories=list(e.get("tags", []) or []),
                published_at=dt,
            )
        )
    return pf


def parse_body(body: bytes, content_type: str) -> ParsedFeed:
    head = body[:512].lstrip()
    if head.startswith(b"{") or "json" in (content_type or ""):
        try:
            return parse_jsonfeed(body)
        except Exception:
            pass
    return parse_feedparser(body)


def fetch_source(db: Session, source: Source) -> int:
    """Fetch one source and upsert its items. Returns the number of new items."""
    settings = get_settings()
    headers = {}
    if source.etag:
        headers["If-None-Match"] = source.etag
    if source.last_modified:
        headers["If-Modified-Since"] = source.last_modified

    source.last_fetched_at = utcnow()
    try:
        with client() as c:
            r = c.get(source.feed_url, headers=headers)
        if r.status_code == 304:
            source.last_success_at = utcnow()
            source.last_error = None
            source.error_count = 0
            db.commit()
            return 0
        r.raise_for_status()
        parsed = parse_body(r.content, r.headers.get("content-type", ""))
    except (httpx.HTTPError, ValueError) as e:
        source.last_error = str(e)[:1000]
        source.error_count += 1
        db.commit()
        return 0

    source.etag = r.headers.get("etag")
    source.last_modified = r.headers.get("last-modified")
    if parsed.title and not source.title:
        source.title = parsed.title[:500]
    if parsed.description and not source.description:
        source.description = to_text(parsed.description)[:2000]
    if parsed.site_url and not source.site_url:
        source.site_url = parsed.site_url

    existing = {g for (g,) in db.execute(select(Item.guid).where(Item.source_id == source.id))}
    new = 0
    for e in parsed.entries:
        if e.guid in existing:
            continue
        existing.add(e.guid)
        html_for_text = e.content or e.summary
        db.add(
            Item(
                source_id=source.id,
                guid=e.guid[:2048],
                url=e.url[:2048],
                title=to_text(e.title)[:1000],
                author=e.author[:255],
                summary=e.summary,
                content=e.content,
                text=to_text(html_for_text)[:20000],
                image_url=(e.image_url or None) and e.image_url[:2048],
                categories="\n".join(c[:100] for c in e.categories),
                published_at=e.published_at or utcnow(),
            )
        )
        new += 1

    source.last_success_at = utcnow()
    source.last_error = None
    source.error_count = 0
    db.commit()

    # Trim to the newest N items so the database doesn't grow without bound.
    ids = db.execute(
        select(Item.id).where(Item.source_id == source.id).order_by(Item.published_at.desc()).offset(settings.max_items_per_source)
    ).scalars().all()
    if ids:
        for item in db.execute(select(Item).where(Item.id.in_(ids))).scalars():
            db.delete(item)
        db.commit()
    return new
