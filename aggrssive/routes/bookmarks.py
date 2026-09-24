"""Bookmark lists: hand-picked pages, described automatically, bundled like any feed."""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import can_manage, require_user
from ..db import get_db
from ..feeds.bookmarks import BOOKMARKS_KIND, extract
from ..feeds.discover import normalize_url
from ..models import Item, Source, User, utcnow
from ..templating import templates
from .sources import get_or_create_tag

router = APIRouter()


def _slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40] or "list"


def my_lists(db: Session, user: User) -> list[Source]:
    return db.execute(select(Source).where(Source.kind == BOOKMARKS_KIND, Source.added_by_id == user.id).order_by(Source.title)).scalars().all()


def _list_for(db: Session, user: User, list_id: int) -> Source:
    s = db.get(Source, list_id)
    if s is None or s.kind != BOOKMARKS_KIND:
        raise HTTPException(404, "No such bookmark list")
    if not can_manage(user, s.added_by_id):
        raise HTTPException(403, "Only the list's owner (or a site admin) can change it")
    return s


@router.get("/bookmarks")
def bookmarks_page(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
    lists = my_lists(db, user)
    counts = dict(db.execute(select(Item.source_id, func.count(Item.id)).where(Item.source_id.in_([s.id for s in lists])).group_by(Item.source_id)).all()) if lists else {}
    others = db.execute(select(Source).where(Source.kind == BOOKMARKS_KIND, Source.added_by_id != user.id).order_by(Source.title)).scalars().all()
    return templates.TemplateResponse(request, "bookmarks.html", {"user": user, "lists": lists, "counts": counts, "others": others})


@router.post("/bookmarks/lists")
def create_list(title: str = Form(...), description: str = Form(""), db: Session = Depends(get_db), user: User = Depends(require_user)):
    title = title.strip()[:200]
    if not title:
        raise HTTPException(400, "Give the list a name")
    base = f"bookmarks://{user.id}/{_slug(title)}"
    url, n = base, 2
    while db.execute(select(Source).where(Source.feed_url == url)).scalar_one_or_none():
        url = f"{base}-{n}"
        n += 1
    s = Source(feed_url=url, title=title, description=description.strip()[:2000], kind=BOOKMARKS_KIND, added_by_id=user.id, last_success_at=utcnow())
    db.add(s)
    db.commit()
    return RedirectResponse(f"/bookmarks/add?list={s.id}", status_code=303)


@router.get("/bookmarks/add")
def add_page(request: Request, url: str = "", title: str = "", list: int | None = None, db: Session = Depends(get_db), user: User = Depends(require_user)):
    lists = my_lists(db, user)
    if not lists:
        return templates.TemplateResponse(request, "bookmark_add.html", {"user": user, "lists": [], "page": None, "url": url, "list_id": None, "given_title": title})
    page = extract(normalize_url(url)) if url.strip() else None
    if page and not page.title:
        page.title = title
    return templates.TemplateResponse(request, "bookmark_add.html", {"user": user, "lists": lists, "page": page, "url": url, "list_id": list or lists[0].id, "given_title": title})


@router.post("/bookmarks/items")
def save_bookmark(
    list_id: int = Form(...),
    url: str = Form(...),
    title: str = Form(""),
    description: str = Form(""),
    note: str = Form(""),
    author: str = Form(""),
    image_url: str = Form(""),
    published: str = Form(""),
    tags: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    lst = _list_for(db, user, list_id)
    url = normalize_url(url)[:2048]
    if db.execute(select(Item).where(Item.source_id == lst.id, Item.guid == url)).scalar_one_or_none():
        return RedirectResponse(f"/sources/{lst.id}?already=1", status_code=303)
    when = None
    if published.strip():
        try:
            when = datetime.fromisoformat(published.strip())
            when = when if when.tzinfo else when.replace(tzinfo=timezone.utc)
        except ValueError:
            when = None
    names = [t.strip().lower().lstrip("#") for t in tags.replace(";", ",").split(",") if t.strip()]
    for n in names:  # bookmark tags join the shared vocabulary so Find feeds knows them
        get_or_create_tag(db, n)
    desc_html = f"<p>{html.escape(description.strip())}</p>" if description.strip() else ""
    note_html = f"<p><em>{html.escape(note.strip())}</em></p>" if note.strip() else ""
    item = Item(
        source_id=lst.id,
        guid=url,
        url=url,
        title=title.strip()[:1000] or url,
        author=author.strip()[:255],
        summary=desc_html + note_html,
        content="",
        text=" ".join(x for x in (title.strip(), description.strip(), note.strip()) if x)[:20000],
        image_url=image_url.strip()[:2048] or None,
        categories="\n".join(names),
        published_at=when or utcnow(),
    )
    db.add(item)
    lst.last_success_at = utcnow()
    db.commit()
    return RedirectResponse(f"/sources/{lst.id}", status_code=303)


@router.post("/bookmarks/items/{item_id}/delete")
def delete_bookmark(item_id: int, db: Session = Depends(get_db), user: User = Depends(require_user)):
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(404)
    lst = _list_for(db, user, item.source_id)
    db.delete(item)
    db.commit()
    return RedirectResponse(f"/sources/{lst.id}", status_code=303)
