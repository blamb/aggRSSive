from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from ..auth import can_manage, current_user, require_user
from ..db import get_db
from ..models import Bundle, Item, Rule, Source, User, bundle_sources
from ..rules import FIELDS, bundle_items, get_override
from ..templating import templates

router = APIRouter()


def load_bundle(db: Session, slug: str) -> Bundle:
    b = db.execute(select(Bundle).where(Bundle.slug == slug).options(selectinload(Bundle.sources), selectinload(Bundle.overrides), selectinload(Bundle.owner))).scalar_one_or_none()
    if not b:
        raise HTTPException(404, "No such aggRSSive")
    return b


def can_view(b: Bundle, user: User | None) -> bool:
    return b.is_public or can_manage(user, b.owner_id)


def can_edit(b: Bundle, user: User | None) -> bool:
    return can_manage(user, b.owner_id)


@router.get("/bundles")
def list_bundles(request: Request, db: Session = Depends(get_db), user: User | None = Depends(current_user)):
    stmt = select(Bundle).options(selectinload(Bundle.owner), selectinload(Bundle.sources)).order_by(Bundle.updated_at.desc())
    if user:
        mine = db.execute(stmt.where(Bundle.owner_id == user.id)).scalars().all()
        others = db.execute(stmt.where(Bundle.is_public.is_(True), Bundle.owner_id != user.id)).scalars().all()
    else:
        mine, others = [], db.execute(stmt.where(Bundle.is_public.is_(True))).scalars().all()
    return templates.TemplateResponse(request, "bundles.html", {"user": user, "mine": mine, "others": others})


@router.post("/bundles")
def create_bundle(title: str = Form(...), source_ids: list[int] = Form([]), description: str = Form(""), user: User = Depends(require_user), db: Session = Depends(get_db)):
    b = Bundle(owner_id=user.id, title=title.strip()[:300] or "Untitled aggRSSive", description=description.strip())
    db.add(b)
    db.flush()
    _set_sources(db, b, source_ids)
    db.commit()
    return RedirectResponse(f"/bundles/{b.slug}/edit", status_code=303)


def _set_sources(db: Session, b: Bundle, source_ids: list[int], append: bool = False) -> None:
    current = {s.id for s in b.sources}
    if append:
        new_ids = [i for i in source_ids if i not in current]
        start = len(current)
    else:
        db.execute(delete(bundle_sources).where(bundle_sources.c.bundle_id == b.id))
        new_ids, start = source_ids, 0
    valid = {s.id for s in db.execute(select(Source).where(Source.id.in_(new_ids))).scalars()} if new_ids else set()
    for pos, sid in enumerate(new_ids, start=start):
        if sid in valid:
            db.execute(bundle_sources.insert().values(bundle_id=b.id, source_id=sid, position=pos))
    db.expire(b, ["sources"])


@router.post("/bundles/{slug}/sources")
def add_sources(slug: str, source_ids: list[int] = Form([]), user: User = Depends(require_user), db: Session = Depends(get_db)):
    b = load_bundle(db, slug)
    if not can_edit(b, user):
        raise HTTPException(403)
    _set_sources(db, b, source_ids, append=True)
    db.commit()
    return RedirectResponse(f"/bundles/{b.slug}/edit", status_code=303)


@router.post("/bundles/{slug}/sources/{source_id}/remove")
def remove_source(slug: str, source_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    b = load_bundle(db, slug)
    if not can_edit(b, user):
        raise HTTPException(403)
    db.execute(delete(bundle_sources).where(bundle_sources.c.bundle_id == b.id, bundle_sources.c.source_id == source_id))
    db.commit()
    return RedirectResponse(f"/bundles/{b.slug}/edit", status_code=303)


@router.get("/bundles/{slug}")
def show_bundle(request: Request, slug: str, db: Session = Depends(get_db), user: User | None = Depends(current_user)):
    b = load_bundle(db, slug)
    if not can_view(b, user):
        raise HTTPException(404, "No such aggRSSive")
    items = bundle_items(db, b)
    return templates.TemplateResponse(request, "bundle.html", {"user": user, "bundle": b, "items": items, "editable": can_edit(b, user)})


@router.get("/bundles/{slug}/edit")
def edit_bundle_page(request: Request, slug: str, db: Session = Depends(get_db), user: User = Depends(require_user)):
    b = load_bundle(db, slug)
    if not can_edit(b, user):
        raise HTTPException(403, "Not yours to edit")
    rules = db.execute(select(Rule).where(Rule.owner_type == "bundle", Rule.owner_id == b.id).order_by(Rule.id)).scalars().all()
    # Preview: what the rules produce, plus what they excluded (so rules can be tuned)
    included = bundle_items(db, b, include_hidden=True)
    included_ids = {bi.item.id for bi in included}
    sids = [s.id for s in b.sources]
    recent = db.execute(select(Item).where(Item.source_id.in_(sids)).options(selectinload(Item.source)).order_by(Item.published_at.desc()).limit(150)).scalars().all() if sids else []
    excluded = [i for i in recent if i.id not in included_ids][:40]
    overrides = {o.item_id: o for o in b.overrides}
    return templates.TemplateResponse(
        request,
        "bundle_edit.html",
        {"user": user, "bundle": b, "rules": rules, "included": included, "excluded": excluded, "overrides": overrides, "fields": FIELDS},
    )


@router.post("/bundles/{slug}/edit")
def edit_bundle(
    slug: str,
    title: str = Form(...),
    description: str = Form(""),
    is_public: bool = Form(False),
    match_mode: str = Form("any"),
    max_age_days: str = Form(""),
    max_items: int = Form(50),
    dedupe: bool = Form(False),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    b = load_bundle(db, slug)
    if not can_edit(b, user):
        raise HTTPException(403)
    b.title = title.strip()[:300] or b.title
    b.description = description.strip()
    b.is_public = is_public
    b.match_mode = "all" if match_mode == "all" else "any"
    b.max_age_days = int(max_age_days) if max_age_days.strip().isdigit() and int(max_age_days) > 0 else None
    b.max_items = max(1, min(max_items, 500))
    b.dedupe = dedupe
    db.commit()
    return RedirectResponse(f"/bundles/{b.slug}/edit", status_code=303)


@router.post("/bundles/{slug}/rules")
def add_bundle_rule(slug: str, kind: str = Form(...), field: str = Form("any"), pattern: str = Form(...), is_regex: bool = Form(False), user: User = Depends(require_user), db: Session = Depends(get_db)):
    b = load_bundle(db, slug)
    if not can_edit(b, user):
        raise HTTPException(403)
    if kind not in ("include", "exclude") or field not in FIELDS or not pattern.strip():
        raise HTTPException(400, "Bad rule")
    db.add(Rule(owner_type="bundle", owner_id=b.id, kind=kind, field=field, pattern=pattern.strip()[:500], is_regex=is_regex))
    db.commit()
    return RedirectResponse(f"/bundles/{b.slug}/edit", status_code=303)


@router.post("/bundles/{slug}/items/{item_id}")
def curate_item(slug: str, item_id: int, action: str = Form(...), note: str = Form(""), user: User = Depends(require_user), db: Session = Depends(get_db)):
    b = load_bundle(db, slug)
    if not can_edit(b, user):
        raise HTTPException(403)
    if not db.get(Item, item_id):
        raise HTTPException(404)
    o = get_override(db, b.id, item_id, create=True)
    if action == "pin":
        o.pinned, o.hidden = True, False
    elif action == "unpin":
        o.pinned = False
    elif action == "hide":
        o.hidden, o.pinned = True, False
    elif action == "unhide":
        o.hidden = False
    elif action == "note":
        o.note = note.strip()[:2000]
    if not (o.pinned or o.hidden or o.note):
        db.delete(o)
    db.commit()
    return RedirectResponse(f"/bundles/{b.slug}/edit#item-{item_id}", status_code=303)


@router.post("/bundles/{slug}/delete")
def delete_bundle(slug: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    b = load_bundle(db, slug)
    if not can_edit(b, user):
        raise HTTPException(403)
    db.execute(delete(Rule).where(Rule.owner_type == "bundle", Rule.owner_id == b.id))
    db.delete(b)
    db.commit()
    return RedirectResponse("/bundles", status_code=303)
