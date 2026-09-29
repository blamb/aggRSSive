"""Email digest subscriptions: subscribe from a bundle page, unsubscribe from a link, test from Admin."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import digest
from ..auth import require_site_admin, require_user
from ..config import get_settings
from ..db import get_db
from ..models import Bundle, Digest, User
from ..templating import templates
from .bundles import can_view, load_bundle

router = APIRouter()


@router.post("/bundles/{slug}/digest")
def set_digest(slug: str, frequency: str = Form("off"), user: User = Depends(require_user), db: Session = Depends(get_db)):
    b = load_bundle(db, slug)
    if not can_view(b, user):
        raise HTTPException(404)
    d = db.execute(select(Digest).where(Digest.user_id == user.id, Digest.bundle_id == b.id)).scalar_one_or_none()
    if frequency in digest.FREQUENCIES:
        if d is None:
            db.add(Digest(user_id=user.id, bundle_id=b.id, frequency=frequency))
        else:
            d.frequency = frequency
    elif d is not None:
        db.delete(d)
    db.commit()
    return RedirectResponse(f"/bundles/{b.slug}", status_code=303)


@router.get("/digests/unsubscribe/{token}")
def unsubscribe(request: Request, token: str, db: Session = Depends(get_db)):
    d = digest.digest_from_token(db, token)
    title = d.bundle.title if d else None
    if d:
        db.delete(d)
        db.commit()
    return templates.TemplateResponse(request, "digest_unsubscribed.html", {"user": None, "title": title})


@router.post("/admin/digest-test")
def digest_test(user: User = Depends(require_site_admin), db: Session = Depends(get_db)):
    if not digest.enabled():
        raise HTTPException(400, "Email is not configured")
    b = db.execute(select(Bundle).where(Bundle.is_public.is_(True)).order_by(Bundle.id)).scalars().first()
    if b is None:
        return RedirectResponse("/admin?mail=nobundle", status_code=303)
    d = Digest(user_id=user.id, bundle_id=b.id, frequency="daily")
    d.id = 0
    d.user, d.bundle = user, b
    from ..rules import bundle_items

    items = bundle_items(db, b, limit=5)
    subject, text, html = digest.render(d, items, get_settings().base_url.rstrip("/"))
    try:
        digest.send_mail(user.email, "[test] " + subject, text, html)
    except Exception as e:  # show the SMTP error on the admin page
        return RedirectResponse(f"/admin?mail=error:{str(e)[:120]}", status_code=303)
    return RedirectResponse("/admin?mail=sent", status_code=303)
