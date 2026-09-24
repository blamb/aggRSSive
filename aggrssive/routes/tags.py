from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..auth import current_user
from ..db import get_db
from ..models import Item, Source, Tag, User, source_tags
from ..templating import order_tags, templates

router = APIRouter()


@router.get("/tags")
def list_tags(request: Request, db: Session = Depends(get_db), user: User | None = Depends(current_user)):
    rows = db.execute(
        select(Tag, func.count(source_tags.c.source_id)).outerjoin(source_tags, Tag.id == source_tags.c.tag_id).group_by(Tag.id).order_by(Tag.name)
    ).all()
    return templates.TemplateResponse(request, "tags.html", {"user": user, "rows": order_tags(rows, user)})


@router.get("/tags/{name}")
def show_tag(request: Request, name: str, db: Session = Depends(get_db), user: User | None = Depends(current_user)):
    t = db.execute(select(Tag).where(Tag.name == name)).scalar_one_or_none()
    if not t:
        raise HTTPException(404, "No such tag")
    sources = db.execute(select(Source).join(source_tags, Source.id == source_tags.c.source_id).where(source_tags.c.tag_id == t.id).options(selectinload(Source.tags)).order_by(Source.title)).scalars().all()
    sids = [s.id for s in sources]
    items = db.execute(select(Item).where(Item.source_id.in_(sids)).options(selectinload(Item.source)).order_by(Item.published_at.desc()).limit(40)).scalars().all() if sids else []
    return templates.TemplateResponse(request, "tag.html", {"user": user, "tag": t, "sources": sources, "items": items})
