from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import current_user
from ..db import get_db
from ..models import Bundle, Item, Source, Tag, User, source_tags
from ..templating import order_tags, templates

router = APIRouter()


@router.get("/")
def home(request: Request, db: Session = Depends(get_db), user: User | None = Depends(current_user)):
    bundles = db.execute(select(Bundle).where(Bundle.is_public.is_(True)).order_by(Bundle.updated_at.desc()).limit(12)).scalars().all()
    tag_counts = db.execute(
        select(Tag, func.count(source_tags.c.source_id)).join(source_tags, Tag.id == source_tags.c.tag_id).group_by(Tag.id).order_by(func.count(source_tags.c.source_id).desc()).limit(60)
    ).all()
    # The home cloud shows the shared vocabulary: tags on two or more feeds. One-off tags still live on Find feeds.
    shared = [(t, n) for t, n in tag_counts if n >= 2]
    tag_counts = (shared if len(shared) >= 12 else tag_counts)[:40]
    stats = {
        "sources": db.scalar(select(func.count(Source.id))),
        "items": db.scalar(select(func.count(Item.id))),
        "bundles": db.scalar(select(func.count(Bundle.id))),
    }
    return templates.TemplateResponse(request, "home.html", {"user": user, "bundles": bundles, "tag_counts": order_tags(tag_counts, user), "stats": stats})
