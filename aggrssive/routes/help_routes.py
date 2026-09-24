from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..auth import current_user
from ..db import get_db
from ..help import pages
from ..models import User
from ..templating import templates

router = APIRouter()


@router.get("/help")
@router.get("/help/{slug}")
def help_page(request: Request, slug: str = "index", db: Session = Depends(get_db), user: User | None = Depends(current_user)):
    all_pages = pages()
    page = all_pages.get(slug)
    if page is None:
        raise HTTPException(404, "No such help page")
    return templates.TemplateResponse(request, "help.html", {"user": user, "page": page, "pages": list(all_pages.values())})
