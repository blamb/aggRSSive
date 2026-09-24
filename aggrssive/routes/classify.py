from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import classification
from ..auth import current_user, require_user
from ..config import get_settings
from ..db import get_db
from ..models import Category, Item, Source, User
from ..templating import templates

router = APIRouter()


@router.get("/classification")
def overview(request: Request, db: Session = Depends(get_db), user: User | None = Depends(current_user)):
    trees = {fw: classification.tree(db, fw) for fw in classification.FRAMEWORKS}
    return templates.TemplateResponse(request, "classification.html", {"user": user, "frameworks": classification.FRAMEWORKS, "trees": trees})


@router.get("/classification/{framework}/{code}")
def show_category(request: Request, framework: str, code: str, db: Session = Depends(get_db), user: User | None = Depends(current_user)):
    c = classification.get(db, f"{framework}:{code}")
    if not c:
        raise HTTPException(404, "No such category")
    sources = classification.sources_under(db, c)
    children = db.execute(select(Category).where(Category.framework == c.framework, Category.parent_code == c.code).order_by(Category.position)).scalars().all()
    sids = [s.id for s in sources]
    items = db.execute(select(Item).where(Item.source_id.in_(sids)).options(selectinload(Item.source)).order_by(Item.published_at.desc()).limit(40)).scalars().all() if sids else []
    return templates.TemplateResponse(
        request,
        "category.html",
        {"user": user, "category": c, "crumbs": classification.ancestors(db, c), "children": children, "sources": sources, "items": items, "meta": classification.FRAMEWORKS[c.framework]},
    )


@router.post("/sources/{source_id}/categories")
def add_category(source_id: int, category: str = Form(...), user: User = Depends(require_user), db: Session = Depends(get_db)):
    s = db.get(Source, source_id)
    if not s:
        raise HTTPException(404)
    # Accept "lcc:LB", or the datalist form "lcc:LB — Theory and practice of education".
    k = category.split("—")[0].split(" ")[0].strip()
    c = classification.get(db, k)
    if c is None:
        hits = classification.search(db, category, limit=1)
        c = hits[0] if hits else None
    if c is None:
        raise HTTPException(400, f"No category matches '{category}'")
    if c not in s.categories:
        s.categories.append(c)
    s.suggested_categories = "\n".join(x for x in s.suggested_categories.split("\n") if x and x != classification.key(c))
    db.commit()
    return RedirectResponse(f"/sources/{s.id}#classification", status_code=303)


@router.post("/sources/{source_id}/categories/{category_id}/remove")
def remove_category(source_id: int, category_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    s = db.get(Source, source_id)
    c = db.get(Category, category_id)
    if s and c and c in s.categories:
        s.categories.remove(c)
        db.commit()
    return RedirectResponse(f"/sources/{source_id}#classification", status_code=303)


@router.post("/sources/{source_id}/categories/suggest")
def suggest_categories(source_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    s = db.get(Source, source_id)
    if not s:
        raise HTTPException(404)
    classification.refresh_suggestions(db, s, use_ai=get_settings().ai_enabled)
    return RedirectResponse(f"/sources/{s.id}#classification", status_code=303)


@router.post("/sources/{source_id}/category-suggestions")
def decide_category(source_id: int, name: str = Form(...), decision: str = Form(...), user: User = Depends(require_user), db: Session = Depends(get_db)):
    s = db.get(Source, source_id)
    if not s:
        raise HTTPException(404)
    keys = [k for k in s.suggested_categories.split("\n") if k] if name == "*" else [name]
    for k in keys:
        classification.decide(db, s, k, accept=decision == "accept")
    return RedirectResponse(f"/sources/{s.id}#classification", status_code=303)
