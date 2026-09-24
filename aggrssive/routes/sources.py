from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from .. import scheduler
from ..auth import current_user, require_user
from ..db import get_db
from ..feeds.discover import discover, normalize_url
from ..feeds.opml import parse_opml
from ..models import Bundle, Item, Rule, Source, Tag, User, source_tags
from ..rules import FIELDS
from ..templating import templates

router = APIRouter()


def get_or_create_tag(db: Session, name: str) -> Tag | None:
    name = name.strip().lower().lstrip("#")[:80]
    if not name:
        return None
    t = db.execute(select(Tag).where(Tag.name == name)).scalar_one_or_none()
    if t is None:
        t = Tag(name=name)
        db.add(t)
        db.flush()
    return t


def add_source(db: Session, feed_url: str, user: User, title: str = "", site_url: str | None = None) -> tuple[Source, bool]:
    """Return (source, created)."""
    existing = db.execute(select(Source).where(Source.feed_url == feed_url)).scalar_one_or_none()
    if existing:
        return existing, False
    s = Source(feed_url=feed_url[:2048], title=title[:500], site_url=site_url, added_by_id=user.id)
    db.add(s)
    db.flush()
    return s, True


def all_tags(db: Session):
    return db.execute(
        select(Tag, func.count(source_tags.c.source_id)).outerjoin(source_tags, Tag.id == source_tags.c.tag_id).group_by(Tag.id).order_by(Tag.name)
    ).all()


@router.get("/sources")
def list_sources(request: Request, q: str = "", tag: str = "", db: Session = Depends(get_db), user: User | None = Depends(current_user)):
    stmt = select(Source).options(selectinload(Source.tags)).order_by(Source.title, Source.feed_url)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Source.title.ilike(like), Source.feed_url.ilike(like), Source.description.ilike(like)))
    if tag:
        stmt = stmt.join(source_tags, Source.id == source_tags.c.source_id).join(Tag, Tag.id == source_tags.c.tag_id).where(Tag.name == tag)
    sources = db.execute(stmt).scalars().all()
    counts = dict(db.execute(select(Item.source_id, func.count(Item.id)).group_by(Item.source_id)).all())
    my_bundles = db.execute(select(Bundle).where(Bundle.owner_id == user.id).order_by(Bundle.title)).scalars().all() if user else []
    return templates.TemplateResponse(
        request, "sources.html", {"user": user, "sources": sources, "counts": counts, "q": q, "tag": tag, "tags": all_tags(db), "my_bundles": my_bundles}
    )


@router.get("/sources/add")
def add_page(request: Request, user: User = Depends(require_user), db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "source_add.html", {"user": user, "candidates": None, "url": "", "error": None, "tags": all_tags(db)})


@router.post("/sources/discover")
def do_discover(request: Request, url: str = Form(...), user: User = Depends(require_user), db: Session = Depends(get_db)):
    try:
        candidates = discover(url)
        error = None if candidates else "No feed found at that address. Try pasting the feed URL directly."
    except ValueError as e:
        candidates, error = [], str(e)
    return templates.TemplateResponse(request, "source_add.html", {"user": user, "candidates": candidates, "url": normalize_url(url), "error": error, "tags": all_tags(db)})


@router.post("/sources")
def create_source(feed_url: str = Form(...), title: str = Form(""), tags: str = Form(""), user: User = Depends(require_user), db: Session = Depends(get_db)):
    s, created = add_source(db, normalize_url(feed_url), user, title=title)
    for name in tags.replace(";", ",").split(","):
        t = get_or_create_tag(db, name)
        if t and t not in s.tags:
            s.tags.append(t)
    db.commit()
    if created:
        scheduler.fetch_soon(s.id)
    return RedirectResponse(f"/sources/{s.id}", status_code=303)


@router.post("/sources/import")
def import_opml(file: UploadFile, use_folders: bool = Form(False), user: User = Depends(require_user), db: Session = Depends(get_db)):
    try:
        entries = parse_opml(file.file.read())
    except Exception as e:
        raise HTTPException(400, f"That doesn't look like OPML: {e}")
    created_ids = []
    for e in entries:
        s, created = add_source(db, e.feed_url, user, title=e.title, site_url=e.site_url)
        if use_folders:
            for folder in e.folders:
                t = get_or_create_tag(db, folder)
                if t and t not in s.tags:
                    s.tags.append(t)
        if created:
            created_ids.append(s.id)
    db.commit()
    for sid in created_ids:
        scheduler.fetch_soon(sid)
    return RedirectResponse(f"/sources?imported={len(created_ids)}", status_code=303)


@router.get("/sources/{source_id}")
def show_source(request: Request, source_id: int, db: Session = Depends(get_db), user: User | None = Depends(current_user)):
    s = db.get(Source, source_id)
    if not s:
        raise HTTPException(404, "No such source")
    items = db.execute(select(Item).where(Item.source_id == s.id).order_by(Item.published_at.desc()).limit(50)).scalars().all()
    rules = db.execute(select(Rule).where(Rule.owner_type == "source", Rule.owner_id == s.id).order_by(Rule.id)).scalars().all()
    in_bundles = db.execute(select(Bundle).join(Bundle.sources).where(Source.id == s.id)).scalars().all()
    return templates.TemplateResponse(
        request, "source.html", {"user": user, "source": s, "items": items, "rules": rules, "in_bundles": in_bundles, "tags": all_tags(db), "fields": FIELDS}
    )


@router.post("/sources/{source_id}/tags")
def tag_source(source_id: int, tags: str = Form(...), user: User = Depends(require_user), db: Session = Depends(get_db)):
    s = db.get(Source, source_id)
    if not s:
        raise HTTPException(404)
    for name in tags.replace(";", ",").split(","):
        t = get_or_create_tag(db, name)
        if t and t not in s.tags:
            s.tags.append(t)
    db.commit()
    return RedirectResponse(f"/sources/{s.id}", status_code=303)


@router.post("/sources/{source_id}/tags/{tag_id}/remove")
def untag_source(source_id: int, tag_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    s = db.get(Source, source_id)
    t = db.get(Tag, tag_id)
    if s and t and t in s.tags:
        s.tags.remove(t)
        db.commit()
    return RedirectResponse(f"/sources/{source_id}", status_code=303)


@router.post("/sources/{source_id}/refresh")
def refresh_source(source_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    s = db.get(Source, source_id)
    if not s:
        raise HTTPException(404)
    s.etag = None
    s.last_modified = None
    db.commit()
    scheduler.fetch_one(s.id)
    return RedirectResponse(f"/sources/{s.id}", status_code=303)


@router.post("/sources/{source_id}/edit")
def edit_source(source_id: int, title: str = Form(""), site_url: str = Form(""), description: str = Form(""), is_active: bool = Form(False), user: User = Depends(require_user), db: Session = Depends(get_db)):
    s = db.get(Source, source_id)
    if not s:
        raise HTTPException(404)
    s.title = title.strip()[:500]
    s.site_url = site_url.strip()[:2048] or None
    s.description = description.strip()[:2000]
    s.is_active = is_active
    db.commit()
    return RedirectResponse(f"/sources/{s.id}", status_code=303)


@router.post("/sources/{source_id}/delete")
def delete_source(source_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    s = db.get(Source, source_id)
    if not s:
        raise HTTPException(404)
    if not (user.is_admin or s.added_by_id == user.id):
        raise HTTPException(403, "Only the person who added a source, or an admin, can delete it.")
    for r in db.execute(select(Rule).where(Rule.owner_type == "source", Rule.owner_id == s.id)).scalars():
        db.delete(r)
    db.delete(s)
    db.commit()
    return RedirectResponse("/sources", status_code=303)


@router.post("/sources/{source_id}/rules")
def add_source_rule(source_id: int, kind: str = Form(...), field: str = Form("any"), pattern: str = Form(...), is_regex: bool = Form(False), user: User = Depends(require_user), db: Session = Depends(get_db)):
    if not db.get(Source, source_id):
        raise HTTPException(404)
    if kind not in ("include", "exclude") or field not in FIELDS or not pattern.strip():
        raise HTTPException(400, "Bad rule")
    db.add(Rule(owner_type="source", owner_id=source_id, kind=kind, field=field, pattern=pattern.strip()[:500], is_regex=is_regex))
    db.commit()
    return RedirectResponse(f"/sources/{source_id}", status_code=303)


@router.post("/rules/{rule_id}/delete")
def delete_rule(rule_id: int, request: Request, user: User = Depends(require_user), db: Session = Depends(get_db)):
    r = db.get(Rule, rule_id)
    if r:
        back = f"/sources/{r.owner_id}" if r.owner_type == "source" else None
        if r.owner_type == "bundle":
            b = db.get(Bundle, r.owner_id)
            if b and b.owner_id != user.id and not user.is_admin:
                raise HTTPException(403)
            back = f"/bundles/{b.slug}/edit" if b else "/bundles"
        db.delete(r)
        db.commit()
        return RedirectResponse(back or "/", status_code=303)
    return RedirectResponse(request.headers.get("referer", "/"), status_code=303)
