"""Public outputs of a bundle: JSON, RSS, Atom, JSON Feed, OPML, embed script, iframe."""

from __future__ import annotations

import json
from datetime import timezone
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from ..auth import current_user
from ..config import get_settings
from ..db import get_db
from ..feeds.opml import OpmlEntry, render_opml
from ..models import Bundle, User, aware
from ..rules import BundleItem, bundle_items
from ..templating import templates
from .bundles import can_view, load_bundle

router = APIRouter()
settings = get_settings()

EMBED_JS = (Path(__file__).parent.parent / "static" / "embed.js").read_text()


def _public_bundle(db: Session, slug: str, user: User | None) -> Bundle:
    b = load_bundle(db, slug)
    if not can_view(b, user):
        raise HTTPException(404, "No such aggRSSive")
    return b


def _n(n: int | None, default: int) -> int:
    return max(1, min(n, 200)) if n else default


def _item_dict(bi: BundleItem, with_content: bool) -> dict:
    i = bi.item
    d = {
        "id": i.id,
        "url": i.url,
        "title": i.title,
        "author": i.author,
        "summary": i.summary,
        "excerpt": (i.text[:280].rsplit(" ", 1)[0] + "…") if len(i.text) > 280 else i.text,
        "image": i.image_url,
        "published": aware(i.published_at).isoformat() if i.published_at else None,
        "source": {"title": i.source.title, "url": i.source.site_url or i.source.feed_url},
        "pinned": bi.pinned,
        "note": bi.note,
    }
    if with_content:
        d["content"] = i.content or i.summary
    return d


@router.get("/b/{slug}.json")
def bundle_json(slug: str, n: int | None = None, content: bool = False, db: Session = Depends(get_db), user: User | None = Depends(current_user)):
    b = _public_bundle(db, slug, user)
    items = bundle_items(db, b, limit=_n(n, b.max_items))
    body = {
        "title": b.title,
        "description": b.description,
        "url": f"{settings.base_url}/bundles/{b.slug}",
        "items": [_item_dict(bi, content) for bi in items],
    }
    return JSONResponse(body, headers={"Access-Control-Allow-Origin": "*", "Cache-Control": "public, max-age=300"})


@router.get("/b/{slug}/feed.json")
def bundle_jsonfeed(slug: str, n: int | None = None, db: Session = Depends(get_db), user: User | None = Depends(current_user)):
    b = _public_bundle(db, slug, user)
    items = bundle_items(db, b, limit=_n(n, b.max_items))
    feed = {
        "version": "https://jsonfeed.org/version/1.1",
        "title": b.title,
        "description": b.description,
        "home_page_url": f"{settings.base_url}/bundles/{b.slug}",
        "feed_url": f"{settings.base_url}/b/{b.slug}/feed.json",
        "items": [
            {
                "id": str(bi.item.id),
                "url": bi.item.url,
                "title": bi.item.title,
                "content_html": bi.item.content or bi.item.summary,
                "summary": bi.item.summary,
                "image": bi.item.image_url,
                "date_published": aware(bi.item.published_at).isoformat() if bi.item.published_at else None,
                "authors": [{"name": bi.item.author}] if bi.item.author else [],
                "_aggrssive": {"source": bi.item.source.title, "pinned": bi.pinned, "note": bi.note},
            }
            for bi in items
        ],
    }
    return Response(json.dumps(feed, ensure_ascii=False), media_type="application/feed+json", headers={"Cache-Control": "public, max-age=300"})


def _rfc822(dt) -> str:
    return format_datetime(aware(dt))


@router.get("/b/{slug}/feed.rss")
def bundle_rss(slug: str, n: int | None = None, db: Session = Depends(get_db), user: User | None = Depends(current_user)):
    b = _public_bundle(db, slug, user)
    items = bundle_items(db, b, limit=_n(n, b.max_items))
    link = f"{settings.base_url}/bundles/{b.slug}"
    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:dc="http://purl.org/dc/elements/1.1/">',
        "<channel>",
        f"<title>{escape(b.title)}</title>",
        f"<link>{escape(link)}</link>",
        f"<description>{escape(b.description)}</description>",
        f'<atom:link href="{escape(settings.base_url)}/b/{b.slug}/feed.rss" rel="self" type="application/rss+xml"/>',
        "<generator>aggRSSive</generator>",
    ]
    for bi in items:
        i = bi.item
        out += [
            "<item>",
            f"<title>{escape(i.title)}</title>",
            f"<link>{escape(i.url)}</link>",
            f'<guid isPermaLink="false">{escape(i.source.feed_url + "#" + i.guid)}</guid>',
            f"<pubDate>{_rfc822(i.published_at)}</pubDate>",
            f"<dc:creator>{escape(i.author)}</dc:creator>" if i.author else "",
            f"<source url=\"{escape(i.source.feed_url, {'\"': '&quot;'})}\">{escape(i.source.title)}</source>",
            f"<description>{escape(i.summary)}</description>",
            f"<content:encoded><![CDATA[{(i.content or i.summary).replace(']]>', ']]]]><![CDATA[>')}]]></content:encoded>" if (i.content or i.summary) else "",
            "</item>",
        ]
    out += ["</channel>", "</rss>"]
    return Response("\n".join(o for o in out if o), media_type="application/rss+xml", headers={"Cache-Control": "public, max-age=300"})


@router.get("/b/{slug}/feed.atom")
def bundle_atom(slug: str, n: int | None = None, db: Session = Depends(get_db), user: User | None = Depends(current_user)):
    b = _public_bundle(db, slug, user)
    items = bundle_items(db, b, limit=_n(n, b.max_items))
    link = f"{settings.base_url}/bundles/{b.slug}"
    updated = aware(items[0].item.published_at if items else b.updated_at).isoformat()
    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<feed xmlns="http://www.w3.org/2005/Atom">',
        f"<title>{escape(b.title)}</title>",
        f"<subtitle>{escape(b.description)}</subtitle>",
        f'<link href="{escape(link)}"/>',
        f'<link rel="self" href="{escape(settings.base_url)}/b/{b.slug}/feed.atom"/>',
        f"<id>{escape(link)}</id>",
        f"<updated>{updated}</updated>",
        "<generator>aggRSSive</generator>",
    ]
    for bi in items:
        i = bi.item
        out += [
            "<entry>",
            f"<title>{escape(i.title)}</title>",
            f'<link href="{escape(i.url)}"/>',
            f"<id>{escape(i.source.feed_url + '#' + i.guid)}</id>",
            f"<updated>{aware(i.published_at).isoformat()}</updated>",
            f"<author><name>{escape(i.author or i.source.title)}</name></author>",
            f"<source><title>{escape(i.source.title)}</title></source>",
            f'<summary type="html">{escape(i.summary)}</summary>',
            f'<content type="html">{escape(i.content or i.summary)}</content>' if (i.content or i.summary) else "",
            "</entry>",
        ]
    out.append("</feed>")
    return Response("\n".join(o for o in out if o), media_type="application/atom+xml", headers={"Cache-Control": "public, max-age=300"})


@router.get("/b/{slug}/sources.opml")
def bundle_opml(slug: str, db: Session = Depends(get_db), user: User | None = Depends(current_user)):
    b = _public_bundle(db, slug, user)
    entries = [OpmlEntry(feed_url=s.feed_url, title=s.title, site_url=s.site_url) for s in b.sources]
    return Response(render_opml(b.title, entries), media_type="text/x-opml", headers={"Content-Disposition": f'attachment; filename="{b.slug}.opml"'})


@router.get("/embed/{slug}.js")
def embed_js(slug: str, db: Session = Depends(get_db), user: User | None = Depends(current_user)):
    _public_bundle(db, slug, user)
    js = EMBED_JS.replace("__BASE__", settings.base_url).replace("__SLUG__", slug)
    return Response(js, media_type="application/javascript", headers={"Cache-Control": "public, max-age=3600", "Access-Control-Allow-Origin": "*"})


@router.get("/embed/{slug}/frame")
def embed_frame(request: Request, slug: str, n: int | None = None, desc: int = 1, img: int = 1, src: int = 1, date: int = 1, theme: str = "light", db: Session = Depends(get_db), user: User | None = Depends(current_user)):
    b = _public_bundle(db, slug, user)
    items = bundle_items(db, b, limit=_n(n, b.max_items))
    return templates.TemplateResponse(
        request,
        "embed_frame.html",
        {"bundle": b, "items": items, "desc": desc, "img": img, "src": src, "date": date, "theme": theme if theme in ("light", "dark", "auto") else "light"},
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.get("/b/{slug}", response_class=HTMLResponse)
def short_link(slug: str):
    from fastapi.responses import RedirectResponse

    return RedirectResponse(f"/bundles/{slug}", status_code=302)
