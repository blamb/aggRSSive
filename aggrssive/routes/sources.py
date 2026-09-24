from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from .. import classification, scheduler, tagging
from ..auth import can_manage, current_user, require_user
from ..config import get_settings
from ..db import get_db
from ..feeds.discover import discover, normalize_url
from ..feeds.opml import parse_opml
from ..models import Bundle, Category, Item, Rule, Source, Tag, User, source_tags
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
def list_sources(request: Request, q: str = "", tag: str = "", cat: str = "", db: Session = Depends(get_db), user: User | None = Depends(current_user)):
    stmt = select(Source).options(selectinload(Source.tags), selectinload(Source.categories)).order_by(Source.title, Source.feed_url)
    category = classification.get(db, cat) if cat else None
    if category:
        stmt = stmt.where(Source.id.in_([x.id for x in classification.sources_under(db, category)]))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Source.title.ilike(like), Source.feed_url.ilike(like), Source.description.ilike(like)))
    if tag:
        stmt = stmt.join(source_tags, Source.id == source_tags.c.source_id).join(Tag, Tag.id == source_tags.c.tag_id).where(Tag.name == tag)
    sources = db.execute(stmt).scalars().all()
    counts = dict(db.execute(select(Item.source_id, func.count(Item.id)).group_by(Item.source_id)).all())
    my_bundles = db.execute(select(Bundle).where(Bundle.owner_id == user.id).order_by(Bundle.title)).scalars().all() if user else []
    return templates.TemplateResponse(
        request, "sources.html", {"user": user, "sources": sources, "counts": counts, "q": q, "tag": tag, "cat": category, "tags": all_tags(db), "my_bundles": my_bundles}
    )


@router.get("/sources/add")
def add_page(request: Request, user: User = Depends(require_user), db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "source_add.html", {"user": user, "candidates": None, "url": "", "error": None, "tags": all_tags(db), "ai": get_settings().ai_enabled})


@router.post("/sources/discover")
def do_discover(request: Request, url: str = Form(...), user: User = Depends(require_user), db: Session = Depends(get_db)):
    try:
        candidates = discover(url)
        error = None if candidates else "No feed found at that address. Try pasting the feed URL directly."
    except ValueError as e:
        candidates, error = [], str(e)
    return templates.TemplateResponse(request, "source_add.html", {"user": user, "candidates": candidates, "url": normalize_url(url), "error": error, "tags": all_tags(db), "ai": get_settings().ai_enabled})


@router.post("/sources")
def create_source(feed_url: str = Form(...), title: str = Form(""), tags: str = Form(""), ai_suggest: bool = Form(False), user: User = Depends(require_user), db: Session = Depends(get_db)):
    s, created = add_source(db, normalize_url(feed_url), user, title=title)
    if ai_suggest and get_settings().ai_enabled:
        s.ai_pending = True
    for name in tags.replace(";", ",").split(","):
        t = get_or_create_tag(db, name)
        if t and t not in s.tags:
            s.tags.append(t)
    db.commit()
    if created:
        scheduler.fetch_soon(s.id)
    return RedirectResponse(f"/sources/{s.id}", status_code=303)


def import_entries(db: Session, entries, user: User, use_folders: bool = True) -> tuple[int, int]:
    """Add OPML entries as sources, applying folders as tags and any classification keys. Returns (created, seen)."""
    created_ids = []
    for e in entries:
        s, created = add_source(db, e.feed_url, user, title=e.title, site_url=e.site_url)
        if use_folders:
            for folder in e.folders:
                t = get_or_create_tag(db, folder)
                if t and t not in s.tags:
                    s.tags.append(t)
        for k in e.categories:
            c = classification.get(db, k)
            if c and c not in s.categories:
                s.categories.append(c)
        if created:
            created_ids.append(s.id)
    db.commit()
    for sid in created_ids:
        scheduler.fetch_soon(sid)
    return len(created_ids), len(entries)


@router.post("/sources/import")
def import_opml(file: UploadFile, use_folders: bool = Form(False), user: User = Depends(require_user), db: Session = Depends(get_db)):
    try:
        entries = parse_opml(file.file.read())
    except Exception as e:
        raise HTTPException(400, f"That doesn't look like OPML: {e}")
    created, _ = import_entries(db, entries, user, use_folders)
    return RedirectResponse(f"/sources?imported={created}", status_code=303)


@router.get("/sources/{source_id}")
def show_source(request: Request, source_id: int, db: Session = Depends(get_db), user: User | None = Depends(current_user)):
    s = db.get(Source, source_id)
    if not s:
        raise HTTPException(404, "No such source")
    items = db.execute(select(Item).where(Item.source_id == s.id).order_by(Item.published_at.desc()).limit(50)).scalars().all()
    rules = db.execute(select(Rule).where(Rule.owner_type == "source", Rule.owner_id == s.id).order_by(Rule.id)).scalars().all()
    in_bundles = db.execute(select(Bundle).join(Bundle.sources).where(Source.id == s.id)).scalars().all()
    suggestions = [n for n in s.suggested_tags.split("\n") if n]
    cat_suggestions = [c for c in (classification.get(db, k) for k in s.suggested_categories.split("\n") if k) if c]
    all_categories = db.execute(select(Category).order_by(Category.framework, Category.position)).scalars().all()
    return templates.TemplateResponse(
        request,
        "source.html",
        {
            "user": user, "source": s, "items": items, "rules": rules, "in_bundles": in_bundles, "tags": all_tags(db), "fields": FIELDS,
            "suggestions": suggestions, "cat_suggestions": cat_suggestions, "all_categories": all_categories, "frameworks": classification.FRAMEWORKS,
            "ai": get_settings().ai_enabled, "ai_model": get_settings().anthropic_model,
        },
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


@router.post("/sources/{source_id}/suggest")
def suggest_tags(source_id: int, ai: bool = Form(False), user: User = Depends(require_user), db: Session = Depends(get_db)):
    s = db.get(Source, source_id)
    if not s:
        raise HTTPException(404)
    tagging.refresh_suggestions(db, s, use_ai=ai and get_settings().ai_enabled)
    return RedirectResponse(f"/sources/{s.id}#suggestions", status_code=303)


@router.post("/sources/{source_id}/suggestions")
def decide_suggestion(source_id: int, name: str = Form(...), decision: str = Form(...), user: User = Depends(require_user), db: Session = Depends(get_db)):
    """Accept or reject one suggestion, or all pending ones (name='*')."""
    s = db.get(Source, source_id)
    if not s:
        raise HTTPException(404)
    accept = decision == "accept"
    names = [n for n in s.suggested_tags.split("\n") if n] if name == "*" else [name]
    for n in names:
        tagging.decide(db, s, n, accept=accept)
    return RedirectResponse(f"/sources/{s.id}#suggestions", status_code=303)


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
    if not can_manage(user, s.added_by_id):
        raise HTTPException(403, "Only the person who added a source, or a site admin, can delete it.")
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
            if b and not can_manage(user, b.owner_id):
                raise HTTPException(403)
            back = f"/bundles/{b.slug}/edit" if b else "/bundles"
        db.delete(r)
        db.commit()
        return RedirectResponse(back or "/", status_code=303)
    return RedirectResponse(request.headers.get("referer", "/"), status_code=303)
