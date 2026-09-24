"""Find feeds: one place to search and browse by tag, by classification heading, or by name."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from .. import classification
from ..auth import current_user
from ..db import get_db
from ..models import Bundle, Category, Source, Tag, User, source_tags
from ..templating import templates

router = APIRouter()


@router.get("/find")
def find(request: Request, q: str = "", db: Session = Depends(get_db), user: User | None = Depends(current_user)):
    q = q.strip()
    tag_counts = db.execute(
        select(Tag, func.count(source_tags.c.source_id)).join(source_tags, Tag.id == source_tags.c.tag_id).group_by(Tag.id).order_by(func.count(source_tags.c.source_id).desc(), Tag.name)
    ).all()
    trees = {fw: [(n, c) for n, c in classification.tree(db, fw)] for fw in classification.FRAMEWORKS}
    my_bundles = db.execute(select(Bundle).where(Bundle.owner_id == user.id).order_by(Bundle.title)).scalars().all() if user else []

    results = None
    if q:
        like = f"%{q}%"
        results = {
            "tags": [(t, n) for t, n in tag_counts if q.lower() in t.name],
            "categories": [(c, next((n for node, n in trees[c.framework] if node.id == c.id), 0)) for c in classification.search(db, q, limit=20)],
            "sources": db.execute(
                select(Source).where(or_(Source.title.ilike(like), Source.description.ilike(like), Source.feed_url.ilike(like))).options(selectinload(Source.tags), selectinload(Source.categories)).order_by(Source.title).limit(40)
            ).scalars().all(),
        }
    total_sources = db.scalar(select(func.count(Source.id)))
    return templates.TemplateResponse(
        request,
        "find.html",
        {"user": user, "q": q, "results": results, "tag_counts": tag_counts, "trees": trees, "frameworks": classification.FRAMEWORKS, "total_sources": total_sources, "my_bundles": my_bundles},
    )
